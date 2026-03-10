"""Knowledge Graph tool definitions for the Microsoft Agent Framework.

Each public function is decorated with ``@tool`` so the agent's LLM can call
it autonomously.  The underlying transport is the MCP SSE server exposed by
knowledge-graph-mcp.

Agent-specific tool factories (which bind ``thread_id``) live in the
individual agent modules.  Raw MCP wrappers (used by orchestration logic) are
also exposed here as plain async functions.
"""

from __future__ import annotations

import json
import os
from typing import Annotated, Any

from agent_framework import tool
from mcp import ClientSession
from mcp.client.sse import sse_client
from pydantic import Field

KG_MCP_URL: str = os.getenv("KG_MCP_URL", "http://localhost:8080").rstrip("/")
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


# ── Raw async wrappers (used by orchestration / non-tool callers) ─────────────

async def kg_health_tool() -> dict:
    """kg_health — check Neo4j, Redis, Ollama availability."""
    return await _call("kg_health", {})


async def kg_query_tool(
    query: str,
    thread_id: str,
    top_k: int = 10,
    max_hops: int = 2,
) -> dict:
    """kg_query — hybrid RAG (vector + graph + LLM)."""
    return await _call("kg_query", {
        "query": query,
        "thread_id": thread_id,
        "top_k": top_k,
        "max_hops": max_hops,
    })


async def kg_retrieve_context_tool(
    query: str,
    thread_id: str,
    top_k: int = 10,
    max_hops: int = 2,
) -> dict:
    """kg_retrieve_context — retrieve docs + graph context WITHOUT LLM generation."""
    return await _call("kg_retrieve_context", {
        "query": query,
        "thread_id": thread_id,
        "top_k": top_k,
        "max_hops": max_hops,
    })


async def kg_ingest_tool(
    file_path: str,
    thread_id: str,
    skip_existing: bool = True,
) -> dict:
    """kg_ingest — ingest a document through the full pipeline."""
    return await _call("kg_ingest", {
        "file_path": file_path,
        "thread_id": thread_id,
        "skip_existing": skip_existing,
    })


async def kg_list_documents_tool(namespace: str) -> dict:
    """kg_list_documents — list all documents in a namespace."""
    return await _call("kg_list_documents", {"namespace": namespace})


async def kg_delete_document_tool(doc_id: str) -> dict:
    """kg_delete_document — remove a document and its chunks."""
    return await _call("kg_delete_document", {"document_id": doc_id})


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


# ── @tool factories — bind thread_id so the LLM never controls it ────────────

def make_query_tools(thread_id: str) -> list:
    """Return @tool functions for query/retrieval, bound to a specific thread."""

    @tool(approval_mode="never_require")
    async def retrieve_kg_context(
        query: Annotated[str, Field(description="The natural-language question to search for in the knowledge graph")],
        top_k: Annotated[int, Field(description="Maximum number of document chunks to retrieve", ge=1, le=50)] = 10,
    ) -> str:
        """Retrieve relevant document chunks and graph context from the Knowledge Graph.

        Returns a JSON object with context_message (raw text for answering),
        sources (list of matching documents), nodes_used, edges_used, and
        has_documents (bool).  Use this before generating any answer.
        """
        result = await kg_retrieve_context_tool(
            query=query, thread_id=thread_id, top_k=top_k, max_hops=2
        )
        return json.dumps(result, ensure_ascii=False)

    @tool(approval_mode="never_require")
    async def search_kg_nodes(
        name: Annotated[str, Field(description="Entity name to look up in the graph")],
    ) -> str:
        """Find a specific entity node in the Knowledge Graph by name."""
        result = await kg_search_nodes_tool(name=name, namespace=thread_id)
        return json.dumps(result, ensure_ascii=False)

    @tool(approval_mode="never_require")
    async def traverse_kg(
        node_id: Annotated[str, Field(description="ID of the node to start traversal from")],
        max_hops: Annotated[int, Field(description="Maximum traversal depth", ge=1, le=4)] = 2,
    ) -> str:
        """Explore the neighbourhood of a node in the Knowledge Graph."""
        result = await kg_traverse_tool(node_id=node_id, max_hops=max_hops)
        return json.dumps(result, ensure_ascii=False)

    return [retrieve_kg_context, search_kg_nodes, traverse_kg]


def make_ingest_tools(thread_id: str) -> list:
    """Return @tool functions for document ingestion, bound to a specific thread."""

    @tool(approval_mode="never_require")
    async def check_kg_health() -> str:
        """Check that the Knowledge Graph API (Neo4j, Redis, Ollama) is available."""
        result = await kg_health_tool()
        return json.dumps(result, ensure_ascii=False)

    @tool(approval_mode="never_require")
    async def list_kg_documents() -> str:
        """List all documents already ingested into the current namespace."""
        result = await kg_list_documents_tool(namespace=thread_id)
        return json.dumps(result, ensure_ascii=False)

    @tool(approval_mode="never_require")
    async def ingest_document(
        file_path: Annotated[str, Field(description="Absolute path to the document file to ingest")],
        skip_existing: Annotated[bool, Field(description="Skip chunks already present (dedup)")] = True,
    ) -> str:
        """Ingest a document file into the Knowledge Graph pipeline.

        Returns chunks_processed, entities_extracted, relations_extracted,
        nodes_created, edges_created, and processing_time_ms.
        """
        result = await kg_ingest_tool(
            file_path=file_path, thread_id=thread_id, skip_existing=skip_existing
        )
        return json.dumps(result, ensure_ascii=False)

    return [check_kg_health, list_kg_documents, ingest_document]


def make_cypher_tools(thread_id: str) -> list:
    """Return @tool functions for Cypher queries, bound to a specific namespace."""

    @tool(approval_mode="never_require")
    async def run_cypher_query(
        query: Annotated[str, Field(description="Read-only Cypher query (MATCH/RETURN only, no writes)")],
    ) -> str:
        """Execute a read-only Cypher query against the Neo4j Knowledge Graph.

        Only MATCH and RETURN statements are allowed — write operations are blocked.
        Always scope to the current namespace; do not use arbitrary namespace values.
        """
        result = await kg_cypher_tool(query=query, namespace=thread_id)
        return json.dumps(result, ensure_ascii=False)

    return [run_cypher_query]


def make_synthesis_tools(thread_id: str) -> list:
    """Return @tool functions for synthesis/report generation."""

    @tool(approval_mode="never_require")
    async def query_kg_with_llm(
        query: Annotated[str, Field(description="Query to run through the full RAG pipeline (vector + graph + LLM)")],
        top_k: Annotated[int, Field(description="Number of results to retrieve", ge=1, le=50)] = 15,
    ) -> str:
        """Run a full RAG query (vector search + graph context + LLM answer) and return the result."""
        result = await kg_query_tool(
            query=query, thread_id=thread_id, top_k=top_k, max_hops=2
        )
        return json.dumps(result, ensure_ascii=False)

    return [query_kg_with_llm]
