"""MCP server entrypoint for Knowledge Graph Lab."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from kg_mcp.config import settings
from kg_mcp import tools

from mcp.server.transport_security import TransportSecuritySettings

mcp = FastMCP(
    "Knowledge Graph Lab",
    instructions=(
        "MCP server for a Knowledge Graph system with Neo4j (graph DB), "
        "Redis (vector store), and Ollama (local LLM). "
        "Use kg_query for RAG questions, kg_ingest to add documents, "
        "kg_cypher for direct graph queries, and kg_traverse to explore relationships."
    ),
    host=settings.MCP_HOST,
    port=settings.MCP_PORT,
    # Disable DNS rebinding protection so the server can bind to 0.0.0.0 in Docker
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


# ── Tool registrations ──────────────────────────────────────────────


@mcp.tool()
async def kg_health() -> str:
    """Check the health status of all Knowledge Graph services (Neo4j, Redis, Ollama).

    Returns JSON with status ("healthy" or "degraded") and individual service booleans.
    """
    return await tools.kg_health()


@mcp.tool()
async def kg_query(
    query: str,
    thread_id: str,
    top_k: int = 10,
    max_hops: int = 2,
) -> str:
    """Query the knowledge graph using hybrid RAG (vector search + graph traversal + LLM).

    Args:
        query: Natural language question about the knowledge graph contents.
        thread_id: Namespace/partition of the data to search (e.g. "default").
        top_k: Number of vector search results to retrieve (default 10).
        max_hops: Maximum graph traversal depth for enrichment (default 2).

    Returns JSON with: answer, sources (doc_id + text_preview + score),
    nodes_used (human-readable node names + types), edges_used (source --[REL]--> target),
    graph_context (formatted nodes + relationships), query_intent, processing_time_ms.
    """
    return await tools.kg_query(query, thread_id, top_k, max_hops)


@mcp.tool()
async def kg_ingest(
    file_path: str,
    thread_id: str,
    skip_existing: bool = True,
) -> str:
    """Ingest a document (PDF, DOCX, or TXT) into the knowledge graph.

    Pipeline: content extraction -> chunking -> embedding -> dedup ->
    entity/relation extraction -> vector store (Redis) + graph store (Neo4j).

    Args:
        file_path: Absolute path to the document file on the server filesystem.
        thread_id: Namespace/partition for the ingested data (e.g. "my-project").
        skip_existing: Skip chunks already present via SHA-256 dedup (default True).

    Returns JSON with: document_id, chunks_processed, chunks_skipped,
    entities_extracted, relations_extracted, nodes_created, edges_created,
    processing_time_ms, errors.
    """
    return await tools.kg_ingest(file_path, thread_id, skip_existing)


@mcp.tool()
async def kg_delete_document(document_id: str) -> str:
    """Delete a document and all its chunks from the vector store (Redis).

    Args:
        document_id: The UUID of the base document to delete.

    Returns JSON confirmation with the deleted document ID.
    """
    return await tools.kg_delete_document(document_id)


@mcp.tool()
async def kg_list_documents(namespace: str) -> str:
    """List all documents stored in a namespace/partition.

    Args:
        namespace: The thread_id to list documents for (e.g. "default").

    Returns JSON array of documents with: id, name, thread_id,
    content_hash, mime_type, page_number, created_at.
    """
    return await tools.kg_list_documents(namespace)


@mcp.tool()
async def kg_search_nodes(name: str, namespace: str) -> str:
    """Search for a knowledge graph node by exact name within a namespace.

    Useful to find a specific entity (Person, Technology, Organization, etc.)
    before traversing its relationships.

    Args:
        name: The entity name to search for (exact match).
        namespace: The namespace/partition (e.g. "default").

    Returns JSON with the node properties or null if not found.
    Node properties include: id, name, label, node_type, importance,
    confidence, description, source_chunk_ids.
    """
    return await tools.kg_search_nodes(name, namespace)


@mcp.tool()
async def kg_traverse(node_id: str, max_hops: int = 2) -> str:
    """Traverse the knowledge graph starting from a node, exploring neighbors.

    Returns all nodes and edges reachable within max_hops from the starting node.
    Useful for understanding the local structure around an entity.

    Args:
        node_id: The UUID of the starting node (get it from kg_search_nodes or kg_query).
        max_hops: Maximum traversal depth, 1-5 (default 2).

    Returns JSON with: nodes (neighbor properties + relationships),
    edges (type, source, target, properties).
    """
    return await tools.kg_traverse(node_id, max_hops)


@mcp.tool()
async def kg_cypher(query: str, params: dict[str, Any] | None = None) -> str:
    """Execute a read-only Cypher query against the Neo4j knowledge graph.

    IMPORTANT: Only read operations are allowed. Write operations
    (CREATE, MERGE, DELETE, SET, REMOVE, DROP) will be rejected.

    Useful for complex graph queries that go beyond simple traversal,
    such as aggregations, path finding, or pattern matching.

    Args:
        query: Cypher query string (e.g. "MATCH (n:KGNode) RETURN n.name, n.node_type LIMIT 20").
        params: Optional query parameters as key-value pairs (e.g. {"name": "Neo4j"}).

    Returns JSON with the query result records.

    Common node label: KGNode. Properties: id, name, label, node_type, namespace,
    importance, confidence, description.
    Relation types: BELONGS_TO, RELATES_TO, CREATED_BY, MENTIONS, PART_OF,
    USES, LOCATED_IN, OCCURRED_AT, HAS_TAG, SIMILAR_TO, DEPENDS_ON, REPLACED_BY.
    """
    return await tools.kg_cypher(query, params)


# ── Entrypoint ──────────────────────────────────────────────────────


def main() -> None:
    """Run the MCP server.

    Transport is selected via MCP_TRANSPORT env var:
      - "stdio"  (default) — for Claude Desktop / Claude Code
      - "sse"    — for Docker / remote access over HTTP
    """
    transport = settings.MCP_TRANSPORT
    if transport == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
