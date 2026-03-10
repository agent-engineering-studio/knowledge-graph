"""Agent run memory — persists AgentRun records in Redis with in-memory fallback.

Primary store: Redis (survives restarts, shared across replicas).
Fallback store: in-process dict (used when Redis is unavailable).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from memory.redis_store import redis_get_run, redis_list_runs, redis_save_run


class AgentRunRecord(BaseModel):
    """Persistent record of a single agent execution."""

    run_id: str
    agent_name: str
    intent: str
    input_summary: str
    output_summary: str
    tool_calls: list[str] = Field(default_factory=list)
    duration_ms: int
    status: str  # "success" | "failed"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# In-process fallback (populated on every save, queried only when Redis is down)
_fallback_store: dict[str, AgentRunRecord] = {}


async def save_agent_run(record: AgentRunRecord) -> None:
    """Persist the run record to Redis (primary) and in-memory dict (fallback).

    Redis write is best-effort: agent execution is never blocked by failures.
    """
    _fallback_store[record.run_id] = record
    try:
        await redis_save_run(record.run_id, record.model_dump())
    except Exception:
        pass


async def get_run(run_id: str) -> AgentRunRecord | None:
    """Retrieve a run record — Redis first, in-memory dict as fallback."""
    try:
        data = await redis_get_run(run_id)
        if data:
            return AgentRunRecord.model_validate(data)
    except Exception:
        pass
    return _fallback_store.get(run_id)


async def list_runs(limit: int = 20) -> list[AgentRunRecord]:
    """Return the most recent run records — Redis first, in-memory as fallback."""
    try:
        data_list = await redis_list_runs(limit)
        if data_list:
            return [AgentRunRecord.model_validate(d) for d in data_list]
    except Exception:
        pass
    return sorted(
        _fallback_store.values(), key=lambda r: r.created_at, reverse=True
    )[:limit]
