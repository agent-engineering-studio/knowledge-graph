"""Redis vector store using RedisSearch and RedisJSON."""

from __future__ import annotations

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
            .no_content()
            .paging(0, 1)
            .dialect(2)
        )
        results = await self._client.ft(self._index_name).search(q)
        if results.total == 0:
            return None
        data = await self._client.json().get(results.docs[0].id)
        if data is None:
            return None
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
            .no_content()
            .paging(0, top_k)
            .dialect(2)
        )

        results = await self._client.ft(self._index_name).search(
            q, query_params={"vec": query_bytes}
        )

        if not results.docs:
            return []

        pipe = self._client.pipeline()
        for doc in results.docs:
            pipe.json().get(doc.id)
        raw_docs = await pipe.execute()

        return [VectorDocument.model_validate(d) for d in raw_docs if d is not None]

    async def get_by_ids(self, doc_ids: list[str]) -> list[VectorDocument]:
        """Fetch multiple documents by their IDs using a pipeline.

        Args:
            doc_ids: List of document IDs (without the ``doc:`` prefix).

        Returns:
            Documents found (missing IDs are silently skipped).
        """
        if not doc_ids:
            return []
        pipe = self._client.pipeline()
        for doc_id in doc_ids:
            pipe.json().get(f"doc:{doc_id}")
        raw_docs = await pipe.execute()
        return [VectorDocument.model_validate(d) for d in raw_docs if d is not None]

    async def update_node_ids(self, doc_id: str, node_ids: list[str]) -> None:
        """Associate Neo4j node IDs with an existing document (partial update).

        Merges with any already-stored node_ids, keeping the list unique.

        Args:
            doc_id: Document ID (without ``doc:`` prefix).
            node_ids: Node IDs extracted from this chunk.
        """
        key = f"doc:{doc_id}"
        existing = await self._client.json().get(key, "$.node_ids")
        current: list[str] = existing[0] if existing else []
        merged = list(dict.fromkeys(current + node_ids))  # dedup, preserve insertion order
        await self._client.json().set(key, "$.node_ids", merged)
        logger.debug("doc_node_ids_updated", doc_id=doc_id, count=len(merged))

    async def keyword_search(
        self,
        terms: list[str],
        namespace: str | None = None,
        top_k: int = 5,
    ) -> list[VectorDocument]:
        """Full-text search on the indexed ``text`` field.

        Uses RedisSearch FT matching so it finds chunks containing the exact
        terms regardless of semantic similarity.

        Args:
            terms: Words to search for (OR-combined).
            namespace: Optional thread_id filter.
            top_k: Maximum number of results.

        Returns:
            Matching documents ordered by FT score.
        """
        if not terms:
            return []
        # Build query: terms OR-combined, scoped to namespace when provided
        escaped = [t.replace("-", "\\-").replace(".", "\\.") for t in terms]
        text_clause = "|".join(f"@text:({w})" for w in escaped)
        if namespace:
            ft_query = f"(@thread_id:{{{namespace}}}) ({text_clause})"
        else:
            ft_query = text_clause

        q = (
            Query(ft_query)
            .no_content()
            .paging(0, top_k)
            .dialect(2)
        )
        try:
            results = await self._client.ft(self._index_name).search(q)
        except Exception as exc:
            logger.warning("keyword_search_failed", error=str(exc))
            return []

        if not results.docs:
            return []

        pipe = self._client.pipeline()
        for doc in results.docs:
            pipe.json().get(doc.id)
        raw_docs = await pipe.execute()
        docs = [VectorDocument.model_validate(d) for d in raw_docs if d is not None]
        logger.debug("keyword_search_done", terms=terms, found=len(docs))
        return docs

    async def delete(self, doc_id: str) -> None:
        """Delete a document from Redis.

        Args:
            doc_id: The document id.
        """
        key = f"doc:{doc_id}"
        await self._client.json().delete(key)
        logger.debug("doc_deleted", doc_id=doc_id)

    async def delete_by_base_id(self, base_document_id: str) -> int:
        """Delete all chunks belonging to a base document.

        Scans all ``doc:*`` keys and removes those whose ``base_document_id``
        matches the given value.

        Args:
            base_document_id: The base document id shared by all chunks.

        Returns:
            Number of chunks deleted.
        """
        deleted = 0
        cursor = 0
        while True:
            cursor, keys = await self._client.scan(cursor, match="doc:*", count=100)
            if keys:
                pipe = self._client.pipeline()
                for key in keys:
                    pipe.json().get(key, "$.base_document_id")
                base_ids = await pipe.execute()

                del_pipe = self._client.pipeline()
                for key, base_id_list in zip(keys, base_ids):
                    if base_id_list and base_id_list[0] == base_document_id:
                        del_pipe.delete(key)
                        deleted += 1
                await del_pipe.execute()
            if cursor == 0:
                break

        logger.info("base_doc_deleted", base_document_id=base_document_id, chunks=deleted)
        return deleted

    async def list_by_namespace(self, namespace: str) -> list[VectorDocument]:
        """List all documents in a namespace.

        Args:
            namespace: The thread_id / namespace.

        Returns:
            List of matching documents.
        """
        q = (
            Query(f"@thread_id:{{{namespace}}}")
            .no_content()
            .paging(0, 1000)
            .dialect(2)
        )
        results = await self._client.ft(self._index_name).search(q)
        if not results.docs:
            return []

        pipe = self._client.pipeline()
        for doc in results.docs:
            pipe.json().get(doc.id)
        raw_docs = await pipe.execute()

        return [VectorDocument.model_validate(d) for d in raw_docs if d is not None]
