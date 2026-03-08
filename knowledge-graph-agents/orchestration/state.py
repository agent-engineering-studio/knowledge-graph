"""Shared AgentState schema for all agents in the multi-agent system."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


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
    """A single step in the agent execution plan."""

    agent: str
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "running", "done", "failed"] = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None


class AgentState(TypedDict):
    """Shared state passed through the LangGraph workflow."""

    user_request: str
    intent: Optional[str]           # Intent enum value
    plan: list[dict]                 # serialised AgentStep list
    current_step: int
    context: dict                    # intermediate data shared between agents
    final_output: Optional[str]
    error: Optional[str]
    thread_id: str                   # KG namespace
    run_id: str                      # UUID of the current run
