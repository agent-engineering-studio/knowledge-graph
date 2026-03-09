"""Thin convenience layer over the Redis vector store for querying."""

from __future__ import annotations

from models.base import VectorDocument
from pipeline.embedder import Embedder
from storage.redis_vector import RedisVectorStore


class VectorSearcher:
    """Wraps embedding + KNN search into a single call."""

    def __init__(self) -> None:
        self.embedder = Embedder()
        self.store = RedisVectorStore()

    async def search(
        self,
        query: str,
        top_k: int = 10,
        namespace: str | None = None,
    ) -> list[VectorDocument]:
        """Embed *query* and return the top-K nearest documents.

        Args:
            query: Natural-language query string.
            top_k: Number of results.
            namespace: Optional thread_id filter.

        Returns:
            Ranked list of vector documents.
        """
        vectors = await self.embedder.embed([query])
        return await self.store.vector_search(vectors[0], top_k=top_k, namespace=namespace)

    async def keyword_search(
        self,
        query: str,
        namespace: str | None = None,
        top_k: int = 5,
    ) -> list[VectorDocument]:
        """Full-text search on chunk content — finds exact term matches.

        Args:
            query: Free-text query; significant words are extracted.
            namespace: Optional thread_id filter.
            top_k: Maximum results.

        Returns:
            Chunks containing the query terms.
        """
        import re
        terms = [w for w in re.sub(r"[^\w\s]", "", query.lower()).split() if len(w) > 2]
        return await self.store.keyword_search(terms, namespace=namespace, top_k=top_k)

    async def fetch_by_ids(self, doc_ids: list[str]) -> list[VectorDocument]:
        """Fetch documents by their IDs directly from Redis.

        Args:
            doc_ids: List of document IDs.

        Returns:
            Documents found (missing IDs silently skipped).
        """
        return await self.store.get_by_ids(doc_ids)
