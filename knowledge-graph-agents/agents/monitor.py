"""Monitor Agent — supervises system health and KG quality."""

from __future__ import annotations

from tools.kg_tools import kg_health_tool
from agents.validator import compute_quality_report
from orchestration.state import AgentState

# Thresholds
QUALITY_ALERT_THRESHOLD = 0.7
LATENCY_WARN_MS = 5000.0


async def monitor_node(state: AgentState) -> AgentState:
    """LangGraph node: collect health + quality metrics and generate a summary."""
    context: dict = dict(state.get("context", {}))
    thread_id: str = state.get("thread_id", "default")

    alerts: list[str] = []
    sections: list[str] = ["# Monitor Report"]

    # ── API Health ────────────────────────────────────────────────────
    try:
        health = await kg_health_tool()
        status = health.get("status", "unknown")
        neo4j_ok = health.get("neo4j", False)
        redis_ok = health.get("redis", False)
        ollama_ok = health.get("ollama", False)

        sections.append(
            f"## Servizi\n"
            f"- API status: **{status}**\n"
            f"- Neo4j: {'✓' if neo4j_ok else '✗ ALERT'}\n"
            f"- Redis: {'✓' if redis_ok else '✗ ALERT'}\n"
            f"- Ollama: {'✓' if ollama_ok else '✗ ALERT'}"
        )

        if not neo4j_ok:
            alerts.append("Neo4j non disponibile")
        if not redis_ok:
            alerts.append("Redis non disponibile")
        if not ollama_ok:
            alerts.append("Ollama non disponibile")

        context["health"] = health
    except Exception as exc:
        sections.append(f"## Servizi\n- Errore health check: {exc}")
        alerts.append(f"Health check fallito: {exc}")

    # ── KG Quality ────────────────────────────────────────────────────
    try:
        report = await compute_quality_report(thread_id)
        context["quality_report"] = report.model_dump()

        health_icon = "✓" if report.overall_health >= QUALITY_ALERT_THRESHOLD else "⚠ ALERT"
        sections.append(
            f"## Qualità KG (namespace: {thread_id})\n"
            f"- Overall health: **{report.overall_health:.0%}** {health_icon}\n"
            f"- Nodi totali: {report.total_nodes}\n"
            f"- Nodi orfani: {report.orphan_nodes}\n"
            f"- Coverage embedding: {report.coverage_score:.0%}"
        )

        if report.overall_health < QUALITY_ALERT_THRESHOLD:
            alerts.append(
                f"Quality score basso: {report.overall_health:.0%} "
                f"(soglia: {QUALITY_ALERT_THRESHOLD:.0%})"
            )
    except Exception as exc:
        sections.append(f"## Qualità KG\n- Errore: {exc}")

    # ── Alerts summary ────────────────────────────────────────────────
    if alerts:
        alert_lines = "\n".join(f"- ⚠ {a}" for a in alerts)
        sections.append(f"## Alert attivi\n{alert_lines}")
    else:
        sections.append("## Alert\n- Nessun alert attivo ✓")

    context["monitor_alerts"] = alerts
    final_output = "\n\n".join(sections)

    return {
        **state,
        "context": context,
        "final_output": final_output,
        "error": None,
    }
