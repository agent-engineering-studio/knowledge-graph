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
