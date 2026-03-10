"""Redis-backed history provider for the Microsoft Agent Framework.

Implements ``BaseContextProvider`` so it can be passed in
``context_providers=[RedisHistoryProvider()]`` when creating an agent.

Conversation history is loaded from Redis before each ``agent.run()`` call and
injected into the agent's system instructions as a formatted text block.
History saving is handled externally by the API layer after the run completes.
"""

from __future__ import annotations

from typing import Any

from agent_framework import BaseContextProvider

from memory.redis_store import redis_get_history


class RedisHistoryProvider(BaseContextProvider):
    """Injects conversation history from Redis into each agent run.

    Usage::

        provider = RedisHistoryProvider()
        agent = client.as_agent(
            name="analyst",
            instructions="...",
            tools=[...],
            context_providers=[provider],
        )

        session = agent.create_session()
        session.state["thread_id"] = thread_id   # required
        result = await agent.run(user_query, session=session)

    The ``thread_id`` key in ``session.state`` identifies the Redis list that
    holds the conversation turns for this session.
    """

    DEFAULT_SOURCE_ID = "redis_history"

    def __init__(self) -> None:
        super().__init__(self.DEFAULT_SOURCE_ID)

    async def before_run(
        self,
        *,
        agent: Any,
        session: Any,
        context: Any,
        state: dict[str, Any],
    ) -> None:
        """Load history from Redis and prepend it to the agent instructions."""
        thread_id: str | None = state.get("thread_id")
        if not thread_id:
            return

        try:
            history = await redis_get_history(thread_id)
        except Exception:
            return

        if not history:
            return

        lines: list[str] = []
        for turn in history:
            role = "User" if turn.get("role") == "user" else "Assistant"
            content = turn.get("content", "")
            lines.append(f"{role}: {content}")

        context.extend_instructions(
            self.source_id,
            "Conversation history (oldest → newest):\n" + "\n".join(lines),
        )

    async def after_run(
        self,
        *,
        agent: Any,
        session: Any,
        context: Any,
        state: dict[str, Any],
    ) -> None:
        """History persistence is handled by the API layer after run completes."""
