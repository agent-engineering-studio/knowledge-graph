"""Agent run memory — persists AgentRun records into the KG via the REST API."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

KG_API_URL: str = os.getenv("KG_API_URL", "http://localhost:8000").rstrip("/")
KG_API_TIMEOUT: float = float(os.getenv("KG_API_TIMEOUT", "60"))


class AgentRunRecord(BaseModel):
    """Persistent record of a single agent execution."""

    run_id: str
    agent_name: str
    intent: str
    input_summary: str
    output_summary: str
    tool_calls: list[str] = Field(default_factory=list)
    duration_ms: int
    status: str                   # "success" | "failed"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_cypher_params(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "agent_name": self.agent_name,
            "intent": self.intent,
            "input_summary": self.input_summary[:500],
            "output_summary": self.output_summary[:500],
            "tool_calls": self.tool_calls,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


# Cypher to write an AgentRun node — the API /graph/cypher endpoint only allows
# reads, so we call /graph/cypher/write which we add to the API, OR we use the
# documented write endpoint.  For Phase 1 we store runs in an in-process dict
# and expose them via /agents/run/{id}.  The KG write is best-effort and
# gracefully skipped if the write endpoint is unavailable.

_WRITE_CYPHER = """
MERGE (r:AgentRun {run_id: $run_id})
SET r.agent_name   = $agent_name,
    r.intent       = $intent,
    r.input_summary  = $input_summary,
    r.output_summary = $output_summary,
    r.tool_calls   = $tool_calls,
    r.duration_ms  = $duration_ms,
    r.status       = $status,
    r.created_at   = $created_at
RETURN r
"""

# In-process store (survives the process, not across restarts)
_run_store: dict[str, AgentRunRecord] = {}


def save_run_local(record: AgentRunRecord) -> None:
    """Persist the record in the in-process store."""
    _run_store[record.run_id] = record


def get_run(run_id: str) -> AgentRunRecord | None:
    """Retrieve a run record by ID from the in-process store."""
    return _run_store.get(run_id)


def list_runs() -> list[AgentRunRecord]:
    """Return all stored run records, newest first."""
    return sorted(_run_store.values(), key=lambda r: r.created_at, reverse=True)


async def save_agent_run(record: AgentRunRecord) -> None:
    """Persist the run record locally and attempt a best-effort write to Neo4j.

    The write to Neo4j uses the ``/graph/cypher/write`` endpoint which must be
    added to knowledge-graph-api.  If that endpoint is absent the error is
    silently swallowed so agent execution is never blocked by memory writes.
    """
    save_run_local(record)

    try:
        async with httpx.AsyncClient(
            base_url=KG_API_URL, timeout=KG_API_TIMEOUT
        ) as client:
            r = await client.post(
                "/graph/cypher/write",
                json={
                    "query": _WRITE_CYPHER,
                    "params": record.to_cypher_params(),
                },
            )
            r.raise_for_status()
    except Exception:
        # Best-effort: do not crash agent execution on memory write failures
        pass
