"""HTTP wrappers around knowledge-graph-api endpoints.

Each function is a thin async wrapper that calls the REST API.
Config is read from the KG_API_URL and KG_API_TIMEOUT environment variables.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

KG_API_URL: str = os.getenv("KG_API_URL", "http://localhost:8000").rstrip("/")
KG_API_TIMEOUT: float = float(os.getenv("KG_API_TIMEOUT", "60"))


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=KG_API_URL, timeout=KG_API_TIMEOUT)


# ── Health ────────────────────────────────────────────────────────────────────

async def kg_health_tool() -> dict:
    """GET /health — check Neo4j, Redis, Ollama availability."""
    async with _client() as c:
        r = await c.get("/health")
        r.raise_for_status()
        return r.json()


# ── Query ─────────────────────────────────────────────────────────────────────

async def kg_query_tool(
    query: str,
    thread_id: str,
    top_k: int = 10,
    max_hops: int = 2,
) -> dict:
    """POST /query — hybrid RAG (vector + graph + LLM).

    Returns:
        RAGResponse dict with ``answer``, ``sources``, ``nodes_used``,
        ``edges_used``, ``query_intent``, ``processing_time_ms``.
    """
    async with _client() as c:
        r = await c.post(
            "/query",
            json={
                "query": query,
                "thread_id": thread_id,
                "top_k": top_k,
                "max_hops": max_hops,
            },
        )
        r.raise_for_status()
        return r.json()


# ── Ingest ────────────────────────────────────────────────────────────────────

async def kg_ingest_tool(
    file_path: str,
    thread_id: str,
    skip_existing: bool = True,
) -> dict:
    """POST /ingest — ingest a document through the full pipeline.

    Returns:
        IngestResult dict with ``document_id``, ``chunks_processed``,
        ``entities_extracted``, ``relations_extracted``, etc.
    """
    async with _client() as c:
        r = await c.post(
            "/ingest",
            json={
                "file_path": file_path,
                "thread_id": thread_id,
                "skip_existing": skip_existing,
            },
        )
        r.raise_for_status()
        return r.json()


# ── Documents ─────────────────────────────────────────────────────────────────

async def kg_list_documents_tool(namespace: str) -> dict:
    """GET /documents/{namespace} — list all documents in a namespace."""
    async with _client() as c:
        r = await c.get(f"/documents/{namespace}")
        r.raise_for_status()
        return r.json()


async def kg_delete_document_tool(doc_id: str) -> dict:
    """DELETE /documents/{doc_id} — remove a document and its chunks."""
    async with _client() as c:
        r = await c.delete(f"/documents/{doc_id}")
        r.raise_for_status()
        return r.json()


# ── Graph ─────────────────────────────────────────────────────────────────────

async def kg_search_nodes_tool(name: str, namespace: str) -> dict:
    """POST /graph/nodes/search — find a KG node by exact name."""
    async with _client() as c:
        r = await c.post(
            "/graph/nodes/search",
            json={"name": name, "namespace": namespace},
        )
        r.raise_for_status()
        return r.json()


async def kg_traverse_tool(node_id: str, max_hops: int = 2) -> dict:
    """POST /graph/traverse — explore neighbours up to max_hops."""
    async with _client() as c:
        r = await c.post(
            "/graph/traverse",
            json={"node_id": node_id, "max_hops": max_hops},
        )
        r.raise_for_status()
        return r.json()


async def kg_cypher_tool(
    query: str,
    namespace: str,
    params: dict[str, Any] | None = None,
) -> dict:
    """POST /graph/cypher — execute a read-only Cypher query.

    Write operations are blocked by the API guardrail.
    The ``namespace`` parameter is included in params for filtering.
    """
    merged_params = {"namespace": namespace, **(params or {})}
    async with _client() as c:
        r = await c.post(
            "/graph/cypher",
            json={"query": query, "params": merged_params},
        )
        r.raise_for_status()
        return r.json()
