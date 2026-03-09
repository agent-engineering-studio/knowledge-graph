"""MCP client wrappers for the knowledge-graph-mcp server.

Each function calls the corresponding MCP tool exposed by knowledge-graph-mcp
via its SSE transport. Config is read from KG_MCP_URL and KG_API_TIMEOUT.

KG_API_URL / KG_API_TIMEOUT are kept for backwards-compat with agent_api.py
health display (not used for tool calls anymore).
"""

from __future__ import annotations

import json
import os
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client

KG_MCP_URL: str = os.getenv("KG_MCP_URL", "http://localhost:8080").rstrip("/")

# Kept for the health endpoint display in agent_api.py
KG_API_URL: str = os.getenv("KG_API_URL", "http://localhost:8000").rstrip("/")
KG_API_TIMEOUT: float = float(os.getenv("KG_API_TIMEOUT", "60"))


async def _call(tool_name: str, arguments: dict[str, Any]) -> Any:
    """Open an MCP SSE session, call a tool, and return the parsed JSON result."""
    async with sse_client(f"{KG_MCP_URL}/sse", timeout=10.0, sse_read_timeout=600.0) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
    if result.isError:
        err = (result.content[0].text if result.content else "") or "unknown MCP error"
        raise RuntimeError(f"MCP tool '{tool_name}' error: {err}")
    text = result.content[0].text if result.content else "{}"
    if not text:
        raise RuntimeError(f"MCP tool '{tool_name}' returned empty response")
    return json.loads(text)


# ── Health ────────────────────────────────────────────────────────────────────

async def kg_health_tool() -> dict:
    """kg_health — check Neo4j, Redis, Ollama availability."""
    return await _call("kg_health", {})


# ── Query ─────────────────────────────────────────────────────────────────────

async def kg_query_tool(
    query: str,
    thread_id: str,
    top_k: int = 10,
    max_hops: int = 2,
) -> dict:
    """kg_query — hybrid RAG (vector + graph + LLM).

    Returns:
        RAGResponse dict with ``answer``, ``sources``, ``nodes_used``,
        ``edges_used``, ``query_intent``, ``processing_time_ms``.
    """
    return await _call("kg_query", {
        "query": query,
        "thread_id": thread_id,
        "top_k": top_k,
        "max_hops": max_hops,
    })


# ── Ingest ────────────────────────────────────────────────────────────────────

async def kg_ingest_tool(
    file_path: str,
    thread_id: str,
    skip_existing: bool = True,
) -> dict:
    """kg_ingest — ingest a document through the full pipeline.

    Returns:
        IngestResult dict with ``document_id``, ``chunks_processed``, etc.
    """
    return await _call("kg_ingest", {
        "file_path": file_path,
        "thread_id": thread_id,
        "skip_existing": skip_existing,
    })


# ── Documents ─────────────────────────────────────────────────────────────────

async def kg_list_documents_tool(namespace: str) -> dict:
    """kg_list_documents — list all documents in a namespace."""
    return await _call("kg_list_documents", {"namespace": namespace})


async def kg_delete_document_tool(doc_id: str) -> dict:
    """kg_delete_document — remove a document and its chunks."""
    return await _call("kg_delete_document", {"document_id": doc_id})


# ── Graph ─────────────────────────────────────────────────────────────────────

async def kg_search_nodes_tool(name: str, namespace: str) -> dict:
    """kg_search_nodes — find a KG node by exact name."""
    return await _call("kg_search_nodes", {"name": name, "namespace": namespace})


async def kg_traverse_tool(node_id: str, max_hops: int = 2) -> dict:
    """kg_traverse — explore neighbours up to max_hops."""
    return await _call("kg_traverse", {"node_id": node_id, "max_hops": max_hops})


async def kg_cypher_tool(
    query: str,
    namespace: str,
    params: dict[str, Any] | None = None,
) -> dict:
    """kg_cypher — execute a read-only Cypher query."""
    merged_params = {"namespace": namespace, **(params or {})}
    return await _call("kg_cypher", {"query": query, "params": merged_params})
