"""Intent classification router — thin shim for backward-compatibility.

Classification logic has moved to ``agents/orchestrator.classify_intent()``.
"""

from __future__ import annotations

from agents.orchestrator import classify_intent  # re-export
from orchestration.state import Intent

__all__ = ["classify_intent", "Intent"]
