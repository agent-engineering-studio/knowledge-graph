"""FastAPI application exposing the multi-agent system on port 8001."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import time
import uuid
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from memory.kg_memory import AgentRunRecord, get_run, list_runs, save_agent_run
from orchestration.graph import agent_graph
from tools.kg_tools import KG_API_URL, KG_API_TIMEOUT

app = FastAPI(
    title="Knowledge Graph Agent API",
    description="Multi-agent orchestration layer for the Knowledge Graph system",
    version="1.0.0",
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

    The request is routed through the orchestrator → specialist agent(s)
    defined in the LangGraph ``StateGraph``.
    """
    run_id = str(uuid.uuid4())
    start_ms = time.perf_counter()

    initial_state = {
        "user_request": body.request,
        "intent": None,
        "plan": [],
        "current_step": 0,
        "context": body.context or {},
        "final_output": None,
        "error": None,
        "thread_id": body.thread_id,
        "run_id": run_id,
    }

    try:
        final_state = await agent_graph.ainvoke(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {exc}")

    elapsed_ms = int((time.perf_counter() - start_ms) * 1000)
    output = final_state.get("final_output") or "Nessun output generato."
    error = final_state.get("error")
    intent = final_state.get("intent")
    plan = final_state.get("plan", [])
    quality = final_state.get("context", {}).get("quality_report")

    # Persist the run record
    record = AgentRunRecord(
        run_id=run_id,
        agent_name="orchestrator",
        intent=intent or "unknown",
        input_summary=body.request[:200],
        output_summary=output[:200],
        tool_calls=[step.get("action", "") for step in plan],
        duration_ms=elapsed_ms,
        status="failed" if error else "success",
    )
    await save_agent_run(record)

    return AgentRunResponse(
        run_id=run_id,
        intent=intent,
        output=output,
        plan=plan,
        quality=quality,
        duration_ms=elapsed_ms,
        error=error,
    )


@app.get("/agents/run/{run_id}", response_model=AgentRunRecord)
async def get_agent_run(run_id: str) -> AgentRunRecord:
    """Retrieve a stored agent run record by its UUID."""
    record = get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return record


@app.get("/agents/runs")
async def list_agent_runs(limit: int = 20) -> list[AgentRunRecord]:
    """List the most recent agent run records."""
    return list_runs()[:limit]


@app.get("/agents/health")
async def agent_health() -> dict:
    """Check the health of this agent service and the downstream KG API."""
    kg_api_ok = False
    try:
        async with httpx.AsyncClient(
            base_url=KG_API_URL, timeout=KG_API_TIMEOUT
        ) as client:
            r = await client.get("/health")
            kg_api_ok = r.status_code == 200
    except Exception:
        pass

    return {
        "status": "ok",
        "kg_api": kg_api_ok,
        "kg_api_url": KG_API_URL,
    }
