"""Multi-step plan builder for the orchestrator agent."""

from __future__ import annotations

from orchestration.state import AgentStep, Intent


# Maps each intent to an ordered list of (agent, action) pairs
INTENT_PLAN_MAP: dict[Intent, list[tuple[str, str]]] = {
    Intent.INGEST: [
        ("ingestion", "ingest_document"),
        ("validator", "quality_check"),
    ],
    Intent.QUERY: [
        ("analyst", "hybrid_search"),
    ],
    Intent.ANALYZE: [
        ("analyst", "graph_traversal"),
        ("analyst", "vector_search"),
    ],
    Intent.SYNTHESIZE: [
        ("analyst", "hybrid_search"),
        ("synthesis", "generate_report"),
    ],
    Intent.VALIDATE: [
        ("validator", "full_quality_check"),
    ],
    Intent.KGC: [
        ("analyst", "hybrid_search"),
        ("kgc", "find_missing_relations"),
        ("synthesis", "generate_report"),
    ],
    Intent.MONITOR: [
        ("monitor", "system_health_check"),
    ],
    Intent.HEALTH: [
        ("monitor", "health_check"),
    ],
}


def build_plan(intent: Intent, params: dict | None = None) -> list[AgentStep]:
    """Build an ordered list of ``AgentStep`` objects for the given intent.

    Args:
        intent: The classified intent.
        params: Optional extra params attached to every step.

    Returns:
        Ordered list of ``AgentStep``.
    """
    params = params or {}
    steps_def = INTENT_PLAN_MAP.get(intent, [("analyst", "hybrid_search")])
    return [
        AgentStep(agent=agent, action=action, params=params)
        for agent, action in steps_def
    ]
