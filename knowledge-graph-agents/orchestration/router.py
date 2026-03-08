"""Intent classification router — regex-based for Phase 1."""

from __future__ import annotations

import re

from orchestration.state import Intent

# Each intent maps to a list of regex patterns (Italian + English)
INTENT_PATTERNS: dict[Intent, list[str]] = {
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
    """Classify the user request into one of the known intents.

    Uses ordered regex matching.  Falls back to ``Intent.QUERY`` when no
    pattern matches.

    Args:
        user_request: The raw user message.

    Returns:
        The matched ``Intent``.
    """
    text = user_request.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text):
                return intent
    return _DEFAULT_INTENT
