"""Intent enum and AgentStep — shared types for the orchestration layer.

``AgentState`` (LangGraph TypedDict) has been removed as part of the migration
to the Microsoft Agent Framework.  Intent classification and dispatch now live
in ``agents/orchestrator.py``.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Intent(str, Enum):
    INGEST = "ingest"
    QUERY = "query"
    ANALYZE = "analyze"
    SYNTHESIZE = "synthesize"
    VALIDATE = "validate"
    KGC = "kgc"
    MONITOR = "monitor"
    HEALTH = "health"


class AgentStep(BaseModel):
    """A single step in the agent execution plan (kept for API backward-compat)."""

    agent: str
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "running", "done", "failed"] = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
