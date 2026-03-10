"""Plan builder — maps intents to ordered AgentStep sequences.

Kept for test backward-compatibility.  Dispatch logic lives in
``agents/orchestrator.dispatch()``.
"""

from __future__ import annotations

from orchestration.state import AgentStep, Intent

_PLANS: dict[Intent, list[tuple[str, str]]] = {
    Intent.INGEST:    [("ingestion", "ingest"), ("validator", "validate")],
    Intent.QUERY:     [("analyst", "query")],
    Intent.ANALYZE:   [("analyst", "analyze"), ("synthesis", "synthesize")],
    Intent.SYNTHESIZE:[("synthesis", "generate_report")],
    Intent.VALIDATE:  [("validator", "validate")],
    Intent.KGC:       [("analyst", "analyze"), ("kgc", "complete"), ("synthesis", "generate_report")],
    Intent.MONITOR:   [("monitor", "monitor")],
    Intent.HEALTH:    [("monitor", "health_check")],
}


def build_plan(intent: Intent) -> list[AgentStep]:
    """Return the ordered list of AgentSteps for the given intent."""
    steps = _PLANS.get(intent, _PLANS[Intent.QUERY])
    return [AgentStep(agent=agent, action=action) for agent, action in steps]
