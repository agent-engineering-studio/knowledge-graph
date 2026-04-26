"""Tests for pipeline.extractor.EntityExtractor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from pipeline.extractor import EntityExtractor


@pytest.mark.asyncio
async def test_extract_returns_result(mock_ollama_client) -> None:
    """Extractor should return an ExtractionResult (possibly empty)."""
    # Override the chat response to return valid JSON
    chat_resp = MagicMock()
    chat_resp.status_code = 200
    chat_resp.json.return_value = {
        "message": {
            "content": '{"entities": [{"id": "redis", "name": "Redis", "type": "Technology", "description": "Data store.", "importance": 0.8, "confidence": 0.9}], "relations": []}'
        }
    }
    chat_resp.raise_for_status = MagicMock()
    mock_ollama_client.post = AsyncMock(return_value=chat_resp)

    extractor = EntityExtractor()
    result = await extractor.extract("Redis is an in-memory data store.")
    assert len(result.entities) == 1
    assert result.entities[0].name == "Redis"


@pytest.mark.asyncio
async def test_extract_handles_bad_json(mock_ollama_client) -> None:
    """Extractor should gracefully handle unparseable LLM output."""
    bad_resp = MagicMock()
    bad_resp.status_code = 200
    bad_resp.json.return_value = {"message": {"content": "not json at all"}}
    bad_resp.raise_for_status = MagicMock()
    mock_ollama_client.post = AsyncMock(return_value=bad_resp)

    extractor = EntityExtractor()
    result = await extractor.extract("Some text")
    assert len(result.entities) == 0
    assert len(result.relations) == 0
