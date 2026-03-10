"""LangGraph StateGraph — removed in Microsoft Agent Framework migration.

The LangGraph ``StateGraph`` has been replaced by direct async dispatch in
``agents/orchestrator.dispatch()``.  This module is kept as a stub so that
any stale imports do not cause ``ModuleNotFoundError``.
"""

from __future__ import annotations


class _StubGraph:
    """Stub that raises a clear error if invoked."""

    async def ainvoke(self, state: dict) -> dict:
        raise RuntimeError(
            "LangGraph agent_graph has been removed. "
            "Use agents.orchestrator.dispatch() instead."
        )


agent_graph = _StubGraph()
