"""Redis vector store using RedisSearch and RedisJSON."""

from __future__ import annotations

import json

import numpy as np
import redis.asyncio as aioredis
from redis.commands.search.field import NumericField, TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query

from config.settings import settings
from models.base import VectorDocument
from utils.logger import logger


class RedisVectorStore:
    """Async Redis vector store backed by RedisSearch."""

    def __init__(self) -> None:
        self._client = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=False,
        )
        self._index_name = settings.REDIS_INDEX_NAME

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._client.aclose()

    # ── Index management ─────────────────────────────────────────────

    async def create_index(self) -> None:
        """Create the RedisSearch index if it does not already exist."""
        schema = (
            TagField("$.thread_id", as_name="thread_id"),
            TagField("$.content_hash", as_name="content_hash"),
            TextField("$.text", as_name="text"),
            NumericField("$.page_number", as_name="page_number"),
            VectorField(
                "$.vector",
                "FLAT",
                {
                    "TYPE": "FLOAT32",
                    "DIM": settings.REDIS_VECTOR_DIM,
                    "DISTANCE_METRIC": "COSINE",
                },
                as_name="vector",
            ),
        )
        definition = IndexDefinition(prefix=["doc:"], index_type=IndexType.JSON)
        try:
            await self._client.ft(self._index_name).create_index(
                schema, definition=definition
            )
            logger.info("redis_index_created", index=self._index_name)
        except Exception:
            # Index already exists
            logger.debug("redis_index_exists", index=self._index_name)

    # ── CRUD ─────────────────────────────────────────────────────────

    async def upsert(self, doc: VectorDocument) -> None:
        """Store or replace a document in Redis.

        Args:
            doc: The vector document to persist.
        """
        key = f"doc:{doc.id}"
        payload = doc.model_dump(mode="json")
        await self._client.json().set(key, "$", payload)
        logger.debug("doc_upserted", doc_id=doc.id)

    async def get_by_hash(self, content_hash: str) -> VectorDocument | None:
        """Lookup a document by its content SHA-256 hash.

        Args:
            content_hash: The SHA-256 hex digest.

        Returns:
            A ``VectorDocument`` or ``None``.
        """
        q = (
            Query(f"@content_hash:{{{content_hash}}}")
            .return_fields("$")
            .paging(0, 1)
            .dialect(2)
        )
        results = await self._client.ft(self._index_name).search(q)
        if results.total == 0:
            return None
        raw = results.docs[0]["$"]
        data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
        return VectorDocument.model_validate(data)

    async def vector_search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        namespace: str | None = None,
    ) -> list[VectorDocument]:
        """Run a KNN vector similarity search.

        Args:
            query_vector: The 768-D query embedding.
            top_k: Number of results to return.
            namespace: Optional thread_id filter.

        Returns:
            Ranked list of matching documents.
        """
        query_bytes = np.array(query_vector, dtype=np.float32).tobytes()

        filter_expr = f"(@thread_id:{{{namespace}}})" if namespace else "*"
        q = (
            Query(f"{filter_expr}=>[KNN {top_k} @vector $vec AS __vector_score]")
            .sort_by("__vector_score")
            .return_fields("$", "__vector_score")
            .paging(0, top_k)
            .dialect(2)
        )

        results = await self._client.ft(self._index_name).search(
            q, query_params={"vec": query_bytes}
        )

        docs: list[VectorDocument] = []
        for doc in results.docs:
            raw = doc["$"]
            data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
            docs.append(VectorDocument.model_validate(data))
        return docs

    async def delete(self, doc_id: str) -> None:
        """Delete a document from Redis.

        Args:
            doc_id: The document id.
        """
        key = f"doc:{doc_id}"
        await self._client.json().delete(key)
        logger.debug("doc_deleted", doc_id=doc_id)

    async def list_by_namespace(self, namespace: str) -> list[VectorDocument]:
        """List all documents in a namespace.

        Args:
            namespace: The thread_id / namespace.

        Returns:
            List of matching documents.
        """
        q = (
            Query(f"@thread_id:{{{namespace}}}")
            .return_fields("$")
            .paging(0, 1000)
            .dialect(2)
        )
        results = await self._client.ft(self._index_name).search(q)
        docs: list[VectorDocument] = []
        for doc in results.docs:
            raw = doc["$"]
            data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
            docs.append(VectorDocument.model_validate(data))
        return docs
