"""Redis-backed persistence for agent run records and conversation history.

Two stores:
- Run records  → JSON string per run_id + sorted-set index by timestamp
- Conv history → Redis list per thread_id (capped, oldest-first)

Key prefixes are scoped to avoid collision with knowledge-graph-api data
(which uses RedisSearch indexes under different key patterns).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import redis.asyncio as aioredis

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# Key naming — prefix "agent:" keeps our keys separate from KG vector data
_RUN_KEY = "agent:run:"       # agent:run:<run_id>  → JSON string
_RUN_IDX = "agent:runs:idx"   # sorted set: member=run_id, score=unix_timestamp
_HIST_KEY = "agent:history:"  # agent:history:<thread_id> → list of JSON turns
_HIST_MAX = 20                 # keep at most 20 conversation turns per thread


def _redis() -> aioredis.Redis:
    """Return a new async Redis client from the configured URL."""
    return aioredis.from_url(REDIS_URL, decode_responses=True)


# ── Run records ───────────────────────────────────────────────────────────────

async def redis_save_run(run_id: str, data: dict[str, Any]) -> None:
    """Persist a run record and register it in the time-sorted index."""
    async with _redis() as r:
        await r.set(f"{_RUN_KEY}{run_id}", json.dumps(data, default=str))
        await r.zadd(_RUN_IDX, {run_id: time.time()})


async def redis_get_run(run_id: str) -> dict[str, Any] | None:
    """Retrieve a run record by ID. Returns None if not found."""
    async with _redis() as r:
        raw = await r.get(f"{_RUN_KEY}{run_id}")
        return json.loads(raw) if raw else None


async def redis_list_runs(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent run records (newest first)."""
    async with _redis() as r:
        ids = await r.zrevrange(_RUN_IDX, 0, limit - 1)
        results: list[dict[str, Any]] = []
        for rid in ids:
            raw = await r.get(f"{_RUN_KEY}{rid}")
            if raw:
                results.append(json.loads(raw))
        return results


# ── Conversation history ──────────────────────────────────────────────────────

async def redis_append_history(thread_id: str, role: str, content: str) -> None:
    """Append one conversation turn to the thread history.

    History is capped at _HIST_MAX turns using RPUSH + LTRIM so the list
    never grows unbounded. Turns are stored oldest-first (FIFO).

    Args:
        thread_id: KG namespace — used as the session identifier.
        role: "user" or "assistant".
        content: Message text.
    """
    async with _redis() as r:
        key = f"{_HIST_KEY}{thread_id}"
        entry = json.dumps({"role": role, "content": content})
        await r.rpush(key, entry)
        await r.ltrim(key, -_HIST_MAX, -1)


async def redis_get_history(thread_id: str) -> list[dict[str, str]]:
    """Return the conversation history for a thread (oldest turn first).

    Returns an empty list if no history exists or Redis is unreachable.
    """
    async with _redis() as r:
        raw_list = await r.lrange(f"{_HIST_KEY}{thread_id}", 0, -1)
        return [json.loads(item) for item in raw_list]


async def redis_clear_history(thread_id: str) -> None:
    """Delete the conversation history for a thread."""
    async with _redis() as r:
        await r.delete(f"{_HIST_KEY}{thread_id}")
