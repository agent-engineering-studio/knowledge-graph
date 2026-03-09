"""Tests for MCP tools — mock the API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from kg_mcp import tools


@pytest.fixture(autouse=True)
def _mock_client():
    """Patch the module-level client with a mock."""
    with patch.object(tools, "client") as mock:
        # Set up common return values
        mock.health = AsyncMock(return_value={"status": "healthy", "neo4j": True, "redis": True, "ollama": True})
        mock.query = AsyncMock(return_value={
            "answer": "Test answer",
            "sources": [],
            "nodes_used": [],
            "edges_used": [],
            "graph_context": "### Nodes\nNone\n\n### Relationships\nNone",
            "query_intent": "general",
            "processing_time_ms": 100.0,
        })
        mock.ingest = AsyncMock(return_value={
            "document_id": "abc-123",
            "chunks_processed": 5,
            "chunks_skipped": 0,
            "entities_extracted": 3,
            "relations_extracted": 2,
            "nodes_created": 3,
            "edges_created": 2,
            "processing_time_ms": 500.0,
            "errors": [],
        })
        mock.delete_document = AsyncMock(return_value={"deleted": "abc-123"})
        mock.list_documents = AsyncMock(return_value={"documents": []})
        mock.search_node = AsyncMock(return_value={"node": None})
        mock.traverse = AsyncMock(return_value={"nodes": [], "edges": []})
        mock.cypher = AsyncMock(return_value={"records": [{"n": "test"}]})
        yield mock


@pytest.mark.asyncio
async def test_kg_health():
    result = await tools.kg_health()
    assert '"healthy"' in result


@pytest.mark.asyncio
async def test_kg_query():
    result = await tools.kg_query("test question", "default")
    assert '"Test answer"' in result
    tools.client.query.assert_awaited_once_with("test question", "default", 10, 2)


@pytest.mark.asyncio
async def test_kg_ingest():
    result = await tools.kg_ingest("/tmp/test.pdf", "default")
    assert '"abc-123"' in result
    tools.client.ingest.assert_awaited_once_with("/tmp/test.pdf", "default", True)


@pytest.mark.asyncio
async def test_kg_delete_document():
    result = await tools.kg_delete_document("abc-123")
    assert '"abc-123"' in result


@pytest.mark.asyncio
async def test_kg_list_documents():
    result = await tools.kg_list_documents("default")
    assert '"documents"' in result


@pytest.mark.asyncio
async def test_kg_search_nodes():
    result = await tools.kg_search_nodes("Neo4j", "default")
    assert "null" in result
    tools.client.search_node.assert_awaited_once_with("Neo4j", "default")


@pytest.mark.asyncio
async def test_kg_traverse():
    result = await tools.kg_traverse("node-1", 3)
    assert '"nodes"' in result
    tools.client.traverse.assert_awaited_once_with("node-1", 3)


@pytest.mark.asyncio
async def test_kg_cypher():
    result = await tools.kg_cypher("MATCH (n) RETURN n LIMIT 1")
    assert '"records"' in result
    tools.client.cypher.assert_awaited_once_with("MATCH (n) RETURN n LIMIT 1", None)
