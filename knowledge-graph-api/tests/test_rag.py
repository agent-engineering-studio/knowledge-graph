"""Tests for query.rag_pipeline.GraphRAGPipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from query.rag_pipeline import GraphRAGPipeline, QueryOptions, RAGResponse


@pytest.mark.asyncio
async def test_query_returns_rag_response(mock_redis_client, mock_neo4j_driver) -> None:
    """RAG pipeline should return a RAGResponse with no-docs fallback when results are empty.

    The pipeline is no-LLM: intent is keyword-based, answer is built directly
    from retrieved documents and graph nodes. With empty results it returns a
    static fallback message.
    """
    pipeline = GraphRAGPipeline()

    # Mock all I/O at method level to avoid real service calls
    pipeline.searcher.store.vector_search = AsyncMock(return_value=[])
    pipeline.searcher.store.keyword_search = AsyncMock(return_value=[])
    pipeline.searcher.embedder.embed = AsyncMock(return_value=[[0.1] * 768])

    # intent="entity_query" ("what is" ∈ _ENTITY_KEYWORDS) + no node_ids
    # → find_entities is called as fallback
    pipeline.traverser.find_entities = AsyncMock(return_value=[])
    pipeline.traverser.graph.traverse_neighbors = AsyncMock(return_value=[])
    pipeline.traverser.graph.get_relations_batch = AsyncMock(return_value=[])

    result = await pipeline.query("What is Redis?", thread_id="test", options=QueryOptions())

    assert isinstance(result, RAGResponse)
    # "what is" matches _ENTITY_KEYWORDS → entity_query
    assert result.query_intent == "entity_query"
    # No docs and no graph nodes → static English fallback
    assert result.answer == "The provided documents do not contain information about this topic."
    assert result.sources == []
    assert result.nodes_used == []
