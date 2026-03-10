"""Orchestrator — classifies intent and dispatches to the appropriate MAF agent.

Replaces the LangGraph ``StateGraph`` with direct async dispatch.
Each intent maps to one or more ``agent.run()`` calls chained in Python.
Multi-step flows (ingest→validate, kgc→synthesis) are composed here.
"""

from __future__ import annotations

import re

from orchestration.state import Intent

# ── Intent classification (regex-based) ──────────────────────────────────────

_INTENT_PATTERNS: dict[Intent, list[str]] = {
    Intent.INGEST: [
        r"\b(carica|ingest|upload|importa|aggiungi documento|inserisci)\b",
    ],
    Intent.QUERY: [
        r"\b(cosa sai|dimmi|descrivi|spiega|parlami|racconta|what do you know|tell me)\b",
    ],
    Intent.ANALYZE: [
        r"\b(analizza|quante entit|conta|statistiche|quanti nodi|analyse|analyze|count)\b",
    ],
    Intent.SYNTHESIZE: [
        r"\b(report|genera|riassumi|sintesi|summary|generate|create|crea)\b",
    ],
    Intent.VALIDATE: [
        r"\b(valida|verifica qualit|check|qualit|quality|valid)\b",
    ],
    Intent.KGC: [
        r"\b(relazioni mancanti|completa|gap|missing relations|completion|completamento)\b",
    ],
    Intent.MONITOR: [
        r"\b(salute|funziona|status|health|monitor|stato sistema)\b",
    ],
    Intent.HEALTH: [
        r"\b(health check|is.*running|ping|alive)\b",
    ],
}

_DEFAULT_INTENT = Intent.QUERY


def classify_intent(user_request: str) -> Intent:
    """Classify the user request into one of the known intents (regex-based).

    Falls back to ``Intent.QUERY`` when no pattern matches.
    """
    text = user_request.lower()
    for intent, patterns in _INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return intent
    return _DEFAULT_INTENT


# ── Dispatch ──────────────────────────────────────────────────────────────────

class OrchestratorResult:
    """Result of a single orchestration run."""

    def __init__(self, intent: Intent, output: str, steps: list[str], quality: dict | None = None) -> None:
        self.intent = intent
        self.output = output
        self.steps = steps           # names of agents that executed
        self.quality = quality       # KGQualityReport dict (if available)

    @property
    def plan(self) -> list[dict]:
        """Serialised plan for backward-compatible API response."""
        return [{"agent": s, "action": s, "status": "done"} for s in self.steps]


async def dispatch(
    user_request: str,
    thread_id: str,
    context: dict | None = None,
) -> OrchestratorResult:
    """Classify intent and run the appropriate agent(s).

    Multi-step flows are chained sequentially:
    - ingest  → ingestion agent  → validator agent
    - kgc     → analyst agent    → kgc agent → synthesis agent
    - analyze → analyst agent    → synthesis agent
    - others  → single agent

    Args:
        user_request: Raw user message.
        thread_id:    KG namespace / session identifier.
        context:      Optional extra context (e.g. file_path for ingest).
    """
    ctx = context or {}
    intent = classify_intent(user_request)

    # Lazy imports to avoid circular dependencies
    from agents.analyst import run_analyst
    from agents.ingestion import run_ingestion
    from agents.kgc import run_kgc
    from agents.monitor import run_monitor
    from agents.synthesis import run_synthesis
    from agents.validator import run_validator

    # ── Single-agent flows ────────────────────────────────────────────────────

    if intent == Intent.QUERY:
        output = await run_analyst(user_request, thread_id)
        return OrchestratorResult(intent, output, ["analyst"])

    if intent == Intent.VALIDATE:
        output, report = await run_validator(thread_id)
        quality = report.model_dump() if report else None
        return OrchestratorResult(intent, output, ["validator"], quality)

    if intent in (Intent.MONITOR, Intent.HEALTH):
        output, _ = await run_monitor(thread_id)
        return OrchestratorResult(intent, output, ["monitor"])

    # ── Multi-agent flows ─────────────────────────────────────────────────────

    if intent == Intent.INGEST:
        file_path = ctx.get("file_path", "")
        ingest_request = (
            f"Carica il documento: {file_path}" if file_path else user_request
        )
        ingest_output = await run_ingestion(ingest_request, thread_id)
        validate_output, report = await run_validator(thread_id)
        quality = report.model_dump() if report else None
        combined = f"{ingest_output}\n\n{validate_output}"
        return OrchestratorResult(intent, combined, ["ingestion", "validator"], quality)

    if intent == Intent.ANALYZE:
        analyst_output = await run_analyst(user_request, thread_id)
        synth_request = f"Sintetizza l'analisi: {user_request}"
        synth_output = await run_synthesis(synth_request, thread_id)
        combined = f"{analyst_output}\n\n---\n\n{synth_output}"
        return OrchestratorResult(intent, combined, ["analyst", "synthesis"])

    if intent == Intent.SYNTHESIZE:
        synth_output = await run_synthesis(user_request, thread_id)
        return OrchestratorResult(intent, synth_output, ["synthesis"])

    if intent == Intent.KGC:
        analyst_output = await run_analyst(user_request, thread_id)
        kgc_output = await run_kgc(
            f"Trova relazioni mancanti nel grafo. Contesto dall'analisi:\n{analyst_output[:500]}",
            thread_id,
        )
        synth_output = await run_synthesis(
            f"Genera un report sulle relazioni mancanti identificate:\n{kgc_output[:500]}",
            thread_id,
        )
        combined = f"{kgc_output}\n\n---\n\n{synth_output}"
        return OrchestratorResult(intent, combined, ["analyst", "kgc", "synthesis"])

    # Fallback
    output = await run_analyst(user_request, thread_id)
    return OrchestratorResult(intent, output, ["analyst"])


# ── Backward-compat shim for tests ────────────────────────────────────────────

async def orchestrator_node(state: dict) -> dict:
    """Shim used by existing tests — wraps dispatch() in the old state dict API."""
    intent = classify_intent(state.get("user_request", ""))
    from orchestration.planner import build_plan
    plan_steps = build_plan(intent)
    return {
        **state,
        "intent": intent.value,
        "plan": [step.model_dump() for step in plan_steps],
        "current_step": 0,
    }
