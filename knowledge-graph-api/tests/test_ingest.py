"""Tests for pipeline.ingest.IngestionPipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.ingest import IngestionPipeline, IngestOptions


@pytest.mark.asyncio
async def test_ingest_txt_file(mock_ollama_client, mock_neo4j_driver, mock_redis_client) -> None:
    """Ingestion of a plain text file should produce chunks."""
    # Create a temp txt file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Redis is great. Neo4j is great. Ollama is great.")
        tmp_path = f.name

    pipeline = IngestionPipeline()

    # Mock the vector store get_by_hash to return None (no duplicates)
    pipeline.vector_store.get_by_hash = AsyncMock(return_value=None)
    pipeline.vector_store.upsert = AsyncMock()
    pipeline.graph.upsert_node = AsyncMock()
    pipeline.graph.upsert_relation = AsyncMock()

    result = await pipeline.ingest(tmp_path, thread_id="test", options=IngestOptions())

    assert result.chunks_processed >= 1
    assert result.document_id != ""

    Path(tmp_path).unlink(missing_ok=True)
