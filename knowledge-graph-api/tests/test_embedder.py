"""Tests for pipeline.embedder.Embedder."""

import pytest

from pipeline.embedder import Embedder


@pytest.mark.asyncio
async def test_embed_single(mock_ollama_client) -> None:
    """Embedder should return a 768-D vector for a single text."""
    embedder = Embedder()
    vectors = await embedder.embed(["Hello world"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 768


@pytest.mark.asyncio
async def test_embed_batch(mock_ollama_client) -> None:
    """Embedder should return one vector per input text."""
    embedder = Embedder()
    texts = ["First sentence.", "Second sentence.", "Third sentence."]
    vectors = await embedder.embed(texts)
    assert len(vectors) == len(texts)
