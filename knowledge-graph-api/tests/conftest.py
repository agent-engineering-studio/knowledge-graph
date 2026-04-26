"""Shared pytest fixtures — all external services are mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.base import VectorDocument
from models.graph_node import GraphNode
from models.relation import Relation


# ── Sample data ──────────────────────────────────────────────────────

@pytest.fixture
def sample_text() -> str:
    """A multi-paragraph text for chunking tests."""
    return (
        "Redis is an open-source in-memory data structure store. "
        "It is used as a database, cache, and message broker. "
        "Redis supports various data structures such as strings, hashes, lists, sets, and sorted sets.\n\n"
        "Neo4j is a graph database management system. "
        "It stores data as nodes and relationships instead of tables or documents. "
        "Neo4j uses the Cypher query language for querying the graph.\n\n"
        "Ollama allows running large language models locally. "
        "It supports models like Llama 3 and embedding models like nomic-embed-text. "
        "Ollama exposes a simple HTTP API for inference."
    )


@pytest.fixture
def sample_chunk() -> str:
    """A single text chunk."""
    return (
        "Redis is an open-source in-memory data structure store. "
        "It is used as a database, cache, and message broker."
    )


@pytest.fixture
def sample_graph_node() -> GraphNode:
    """A graph node fixture."""
    return GraphNode(
        id="redis_node",
        name="Redis",
        label="Technology",
        node_type="Technology",
        namespace="test",
        importance=0.9,
        confidence=0.95,
        description="In-memory data structure store.",
    )


@pytest.fixture
def sample_relation() -> Relation:
    """A relation fixture."""
    return Relation(
        id="rel_1",
        source_id="redis_node",
        target_id="neo4j_node",
        label="RELATES_TO",
        relation_type="RELATES_TO",
        weight=0.7,
        confidence=0.85,
        namespace="test",
    )


@pytest.fixture
def sample_vector_document() -> VectorDocument:
    """A vector document fixture."""
    return VectorDocument(
        id="doc_1",
        thread_id="test",
        text="Redis is an in-memory data store.",
        name="test.txt",
        vector=[0.1] * 768,
        content_hash="abc123",
    )


# ── Mock fixtures ────────────────────────────────────────────────────

@pytest.fixture
def mock_ollama_client():
    """Mock for Ollama HTTP API calls via httpx."""
    with patch("httpx.AsyncClient") as mock_cls:
        client = AsyncMock()

        # Embedding response (json() is sync in httpx, so use MagicMock)
        embed_response = MagicMock()
        embed_response.status_code = 200
        embed_response.json.return_value = {"embedding": [0.1] * 768}
        embed_response.raise_for_status = MagicMock()

        # Chat response
        chat_response = MagicMock()
        chat_response.status_code = 200
        chat_response.json.return_value = {
            "message": {
                "content": '{"entities": [], "relations": []}'
            }
        }
        chat_response.raise_for_status = MagicMock()

        client.post = AsyncMock(return_value=embed_response)
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        mock_cls.return_value = client
        yield client


@pytest.fixture
def mock_neo4j_driver():
    """Mock for the Neo4j async driver."""
    with patch("neo4j.AsyncGraphDatabase.driver") as mock_driver_fn:
        driver = AsyncMock()
        session = AsyncMock()
        result = AsyncMock()
        result.single = AsyncMock(return_value=None)

        session.run = AsyncMock(return_value=result)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)

        driver.session = MagicMock(return_value=session)
        driver.close = AsyncMock()

        mock_driver_fn.return_value = driver
        yield driver


@pytest.fixture
def mock_redis_client():
    """Mock for the Redis async client."""
    with patch("redis.asyncio.from_url") as mock_from_url:
        client = AsyncMock()
        client.json.return_value.set = AsyncMock()
        client.json.return_value.delete = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        client.ft.return_value.create_index = AsyncMock()
        client.ft.return_value.search = AsyncMock(
            return_value=MagicMock(total=0, docs=[])
        )
        client.aclose = AsyncMock()

        mock_from_url.return_value = client
        yield client
