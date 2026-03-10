"""FastAPI application exposing the multi-agent system on port 8001.

Uses the Microsoft Agent Framework for agent execution.
LangGraph StateGraph has been replaced by agents.orchestrator.dispatch().
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import time
import uuid
from typing import Any, Optional

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.orchestrator import dispatch
from memory.kg_memory import AgentRunRecord, get_run, list_runs, save_agent_run
from memory.redis_store import redis_append_history, redis_clear_history, redis_get_history
from tools.kg_tools import KG_API_URL, KG_API_TIMEOUT

app = FastAPI(
    title="Knowledge Graph Agent API",
    description="Multi-agent orchestration layer — powered by Microsoft Agent Framework",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response schemas ────────────────────────────────────────────────

class AgentRunRequest(BaseModel):
    """Request body for POST /agents/run."""

    request: str
    thread_id: str = "default"
    context: Optional[dict[str, Any]] = None


class AgentRunResponse(BaseModel):
    """Response for POST /agents/run."""

    run_id: str
    intent: Optional[str]
    output: str
    plan: list[dict]
    quality: Optional[dict]
    duration_ms: int
    error: Optional[str]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/agents/run", response_model=AgentRunResponse)
async def run_agent(body: AgentRunRequest) -> AgentRunResponse:
    """Execute the multi-agent workflow for a user request.

    The orchestrator classifies the intent and dispatches to the appropriate
    Microsoft Agent Framework agent(s).  Conversation history is automatically
    injected via ``RedisHistoryProvider`` and saved after successful Q&A turns.
    """
    run_id = str(uuid.uuid4())
    start_ms = time.perf_counter()
    error: str | None = None

    try:
        result = await dispatch(
            user_request=body.request,
            thread_id=body.thread_id,
            context=body.context,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}")

    elapsed_ms = int((time.perf_counter() - start_ms) * 1000)
    output = result.output or "Nessun output generato."

    # Persist Q&A history for conversational intents
    if result.intent.value in ("query", "analyze"):
        try:
            await redis_append_history(body.thread_id, "user", body.request)
            await redis_append_history(body.thread_id, "assistant", output[:1000])
        except Exception:
            pass

    # Persist run record
    record = AgentRunRecord(
        run_id=run_id,
        agent_name="orchestrator",
        intent=result.intent.value,
        input_summary=body.request[:200],
        output_summary=output[:200],
        tool_calls=result.steps,
        duration_ms=elapsed_ms,
        status="failed" if error else "success",
    )
    await save_agent_run(record)

    return AgentRunResponse(
        run_id=run_id,
        intent=result.intent.value,
        output=output,
        plan=result.plan,
        quality=result.quality,
        duration_ms=elapsed_ms,
        error=error,
    )


@app.post("/agents/run/upload", response_model=AgentRunResponse)
async def run_agent_upload(
    file: UploadFile = File(...),
    thread_id: str = Form("default"),
    message: str = Form(""),
) -> AgentRunResponse:
    """Upload a document file and run the ingestion agent workflow."""
    run_id = str(uuid.uuid4())
    start_ms = time.perf_counter()

    # Stage the file on the KG API server
    try:
        async with httpx.AsyncClient(base_url=KG_API_URL, timeout=30.0) as c:
            content = await file.read()
            r = await c.post(
                "/ingest/stage",
                files={"file": (file.filename, content, file.content_type or "application/octet-stream")},
            )
            r.raise_for_status()
            tmp_path: str = r.json()["tmp_path"]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"File staging failed: {exc}")

    request_text = message or f"Carica il documento: {file.filename}"

    try:
        result = await dispatch(
            user_request=request_text,
            thread_id=thread_id,
            context={"file_path": tmp_path, "skip_existing": True},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}")

    elapsed_ms = int((time.perf_counter() - start_ms) * 1000)
    output = result.output or "Ingestion completata."

    record = AgentRunRecord(
        run_id=run_id,
        agent_name="ingestion",
        intent="ingest",
        input_summary=f"[FILE] {file.filename}",
        output_summary=output[:200],
        tool_calls=result.steps,
        duration_ms=elapsed_ms,
        status="success",
    )
    await save_agent_run(record)

    return AgentRunResponse(
        run_id=run_id,
        intent="ingest",
        output=output,
        plan=result.plan,
        quality=result.quality,
        duration_ms=elapsed_ms,
        error=None,
    )


@app.get("/agents/run/{run_id}", response_model=AgentRunRecord)
async def get_agent_run(run_id: str) -> AgentRunRecord:
    """Retrieve a stored agent run record by its UUID."""
    record = await get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return record


@app.get("/agents/runs")
async def list_agent_runs(limit: int = 20) -> list[AgentRunRecord]:
    """List the most recent agent run records."""
    return await list_runs(limit)


@app.get("/agents/history/{thread_id}")
async def get_conversation_history(thread_id: str) -> list[dict]:
    """Return the full conversation history for a thread (oldest turn first)."""
    try:
        return await redis_get_history(thread_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load history: {exc}")


@app.delete("/agents/history/{thread_id}")
async def clear_conversation_history(thread_id: str) -> dict:
    """Clear the conversation history for a thread."""
    try:
        await redis_clear_history(thread_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {exc}")
    return {"cleared": thread_id}


@app.get("/agents/health")
async def agent_health() -> dict:
    """Check the health of this agent service, the downstream KG API, and Redis."""
    kg_api_ok = False
    redis_ok = False

    try:
        async with httpx.AsyncClient(base_url=KG_API_URL, timeout=KG_API_TIMEOUT) as client:
            r = await client.get("/health")
            kg_api_ok = r.status_code == 200
    except Exception:
        pass

    try:
        from memory.redis_store import _redis
        async with _redis() as r:
            await r.ping()
            redis_ok = True
    except Exception:
        pass

    return {
        "status": "ok",
        "framework": "microsoft-agent-framework",
        "kg_api": kg_api_ok,
        "kg_api_url": KG_API_URL,
        "redis": redis_ok,
    }
