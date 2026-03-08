"""Orchestrator Agent — classifies intent and builds the execution plan."""

from __future__ import annotations

from orchestration.planner import build_plan
from orchestration.router import classify_intent
from orchestration.state import AgentState


async def orchestrator_node(state: AgentState) -> AgentState:
    """LangGraph node: classify intent and populate the plan.

    The orchestrator never calls KG tools directly — it only delegates.
    """
    user_request: str = state.get("user_request", "")

    intent = classify_intent(user_request)
    plan_steps = build_plan(intent)

    return {
        **state,
        "intent": intent.value,
        "plan": [step.model_dump() for step in plan_steps],
        "current_step": 0,
        "context": state.get("context", {}),
    }
