"""Monitor Agent — supervises system health and KG quality.

Uses the Microsoft Agent Framework ``client.as_agent()`` + ``AgentSession`` pattern.

All data collection (health check, quality metrics) is done explicitly in Python
so the LLM only needs to format the pre-collected data into a readable report.
This avoids reliance on LLM tool-calling with local models.
"""

from __future__ import annotations

from agent_framework import AgentSession

from agents.client import get_client
from agents.validator import compute_quality_report
from tools.kg_tools import kg_health_tool

QUALITY_ALERT_THRESHOLD = 0.7

_MONITOR_INSTRUCTIONS = """\
You are a system monitoring agent for a Knowledge Graph platform.

## Your task
The user message contains pre-collected health and quality data.
Format it into a clear Monitor Report in this structure:

# Monitor Report

## Servizi
<table or bullet list of service statuses>

## Qualità KG
<quality metrics with health score>

## Alert
<list of active alerts, or "Nessun alert attivo ✓">

Be concise. Use ✓ for OK and ✗ for failures.
"""


def create_monitor_agent(thread_id: str):
    """Create a monitor agent (no tools — data injected in prompt)."""
    client = get_client()
    return client.as_agent(
        name="monitor",
        instructions=_MONITOR_INSTRUCTIONS,
    )


async def run_monitor(thread_id: str) -> tuple[str, dict | None]:
    """Collect health + quality data in Python, then format via MAF agent."""
    health: dict | None = None
    try:
        health = await kg_health_tool()
    except Exception:
        pass

    quality_report = None
    try:
        quality_report = await compute_quality_report(thread_id)
    except Exception:
        pass

    # Build data summary for the LLM to format
    sections: list[str] = []

    if health:
        neo4j = "✓" if health.get("neo4j") else "✗ ALERT"
        redis = "✓" if health.get("redis") else "✗ ALERT"
        ollama = "✓" if health.get("ollama") else "✗ ALERT"
        sections.append(
            f"Service health: API={health.get('status','unknown')}, "
            f"Neo4j={neo4j}, Redis={redis}, Ollama={ollama}"
        )
    else:
        sections.append("Service health: UNREACHABLE")

    if quality_report:
        sections.append(
            f"KG quality (namespace={thread_id}): "
            f"nodes={quality_report.total_nodes}, "
            f"relations={quality_report.total_relations}, "
            f"orphans={quality_report.orphan_nodes}, "
            f"coverage={quality_report.coverage_score:.0%}, "
            f"overall_health={quality_report.overall_health:.0%}"
        )

    alerts: list[str] = []
    if health:
        if not health.get("neo4j"):
            alerts.append("Neo4j non disponibile")
        if not health.get("redis"):
            alerts.append("Redis non disponibile")
        if not health.get("ollama"):
            alerts.append("Ollama non disponibile")
    if quality_report and quality_report.overall_health < QUALITY_ALERT_THRESHOLD:
        alerts.append(f"Quality score basso: {quality_report.overall_health:.0%}")
    if alerts:
        sections.append("Alerts: " + "; ".join(alerts))

    data_summary = "\n".join(sections)
    prompt = f"<monitor_data>\n{data_summary}\n</monitor_data>\n\nGenerate the monitor report."

    agent = create_monitor_agent(thread_id)
    session: AgentSession = agent.create_session()
    session.state["thread_id"] = thread_id

    try:
        report = str(await agent.run(prompt, session=session))
    except Exception as exc:
        # Fallback: build report without LLM
        report = f"# Monitor Report\n\n" + "\n".join(f"- {s}" for s in sections)
        if alerts:
            report += "\n\n## Alert\n" + "\n".join(f"- ⚠ {a}" for a in alerts)

    return report, health
