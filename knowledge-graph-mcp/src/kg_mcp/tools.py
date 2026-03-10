"""MCP tool implementations for Knowledge Graph Lab."""

from __future__ import annotations

import json
from typing import Any

from kg_mcp.api_client import KGApiClient

client = KGApiClient()


def _fmt(data: Any) -> str:
    """Format a dict/list as indented JSON text for the LLM."""
    return json.dumps(data, indent=2, default=str, ensure_ascii=False)


async def kg_health() -> str:
    """Check the health status of all Knowledge Graph services (Neo4j, Redis, Ollama)."""
    result = await client.health()
    return _fmt(result)


async def kg_query(
    query: str,
    thread_id: str,
    top_k: int = 10,
    max_hops: int = 2,
) -> str:
    """Query the knowledge graph using hybrid RAG (vector search + graph traversal + LLM).

    Args:
        query: Natural language question.
        thread_id: Namespace/partition of the data to search.
        top_k: Number of vector search results (default 10).
        max_hops: Max graph traversal depth (default 2).

    Returns:
        Answer with sources, nodes used, edges used, intent classification, and timing.
    """
    result = await client.query(query, thread_id, top_k, max_hops)
    return _fmt(result)


async def kg_ingest(
    file_path: str,
    thread_id: str,
    skip_existing: bool = True,
) -> str:
    """Ingest a document (PDF, DOCX, or TXT) into the knowledge graph.

    The file goes through: content extraction -> chunking -> embedding ->
    dedup -> entity/relation extraction -> vector store + graph store.

    Args:
        file_path: Absolute path to the document file.
        thread_id: Namespace/partition for the ingested data.
        skip_existing: Skip chunks already present (SHA-256 dedup). Default True.

    Returns:
        Ingestion summary with counts of chunks, entities, relations, and timing.
    """
    result = await client.ingest(file_path, thread_id, skip_existing)
    return _fmt(result)


async def kg_delete_document(document_id: str) -> str:
    """Delete a document and all its chunks from the vector store.

    Args:
        document_id: The UUID of the document to delete.

    Returns:
        Confirmation with the deleted document ID.
    """
    result = await client.delete_document(document_id)
    return _fmt(result)


async def kg_list_documents(namespace: str) -> str:
    """List all documents stored in a namespace.

    Args:
        namespace: The thread_id / namespace to list.

    Returns:
        List of documents with id, name, mime_type, content_hash, created_at.
    """
    result = await client.list_documents(namespace)
    return _fmt(result)


async def kg_search_nodes(name: str, namespace: str) -> str:
    """Search for a knowledge graph node by exact name within a namespace.

    Args:
        name: The entity name to search for.
        namespace: The namespace/partition.

    Returns:
        The node properties (id, name, type, importance, confidence, etc.) or null.
    """
    result = await client.search_node(name, namespace)
    return _fmt(result)


async def kg_traverse(node_id: str, max_hops: int = 2) -> str:
    """Traverse the knowledge graph starting from a node, exploring neighbors up to max_hops.

    Args:
        node_id: The UUID of the starting node.
        max_hops: Maximum traversal depth (default 2).

    Returns:
        Neighboring nodes and edges found within the traversal radius.
    """
    result = await client.traverse(node_id, max_hops)
    return _fmt(result)


async def kg_retrieve_context(
    query: str,
    thread_id: str,
    top_k: int = 10,
    max_hops: int = 2,
) -> str:
    """Retrieve documents + graph context WITHOUT LLM generation.

    Calls the same retrieval pipeline as kg_query but remaps the response to
    the RetrievalResult format expected by agent consumers:
      - context_message: structured text with docs + graph nodes (no LLM answer)
      - sources: list of source references
      - nodes_used / edges_used: graph enrichment
      - has_documents: True if any sources or graph nodes were found
    """
    result = await client.query(query, thread_id, top_k, max_hops)
    retrieval = {
        "context_message": result.get("answer", ""),
        "sources": result.get("sources", []),
        "nodes_used": result.get("nodes_used", []),
        "edges_used": result.get("edges_used", []),
        "query_intent": result.get("query_intent", ""),
        "processing_time_ms": result.get("processing_time_ms", 0),
        "has_documents": bool(result.get("sources")) or bool(result.get("nodes_used")),
    }
    return _fmt(retrieval)


async def kg_cypher(query: str, params: dict[str, Any] | None = None) -> str:
    """Execute a read-only Cypher query against the Neo4j graph database.

    Write operations (CREATE, MERGE, DELETE, SET, REMOVE, DROP) are blocked.

    Args:
        query: The Cypher query string (e.g. "MATCH (n:KGNode) RETURN n LIMIT 10").
        params: Optional query parameters as key-value pairs.

    Returns:
        Query result records as a JSON array.
    """
    result = await client.cypher(query, params)
    return _fmt(result)
