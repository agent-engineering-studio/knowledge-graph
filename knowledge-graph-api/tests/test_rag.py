"""Tests for query.rag_pipeline.GraphRAGPipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from query.rag_pipeline import GraphRAGPipeline, QueryOptions, RAGResponse


@pytest.mark.asyncio
async def test_query_returns_rag_response(mock_ollama_client, mock_redis_client, mock_neo4j_driver) -> None:
    """RAG query should return a structured RAGResponse."""
    pipeline = GraphRAGPipeline()

    # Mock vector search to return empty
    pipeline.searcher.store.vector_search = AsyncMock(return_value=[])
    pipeline.searcher.embedder.embed = AsyncMock(return_value=[[0.1] * 768])

    # Mock graph traversal
    pipeline.traverser.graph.traverse_neighbors = AsyncMock(return_value=[])
    pipeline.traverser.graph.get_relations_batch = AsyncMock(return_value=[])

    # Mock intent classification response (json() is sync in httpx)
    intent_resp = MagicMock()
    intent_resp.status_code = 200
    intent_resp.json.return_value = {"message": {"content": "general"}}
    intent_resp.raise_for_status = MagicMock()

    # Mock generation response
    gen_resp = MagicMock()
    gen_resp.status_code = 200
    gen_resp.json.return_value = {"message": {"content": "This is the answer."}}
    gen_resp.raise_for_status = MagicMock()

    mock_ollama_client.post = AsyncMock(side_effect=[intent_resp, gen_resp])

    result = await pipeline.query("What is Redis?", thread_id="test", options=QueryOptions())

    assert isinstance(result, RAGResponse)
    assert result.answer == "This is the answer."
    assert result.query_intent == "general"
