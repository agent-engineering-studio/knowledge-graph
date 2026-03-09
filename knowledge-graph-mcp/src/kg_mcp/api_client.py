"""Typed HTTP client for knowledge-graph-api."""

from __future__ import annotations

from typing import Any

import httpx

from kg_mcp.config import settings


class KGApiClient:
    """Async HTTP client wrapping all knowledge-graph-api endpoints."""

    def __init__(self) -> None:
        self._base = settings.KG_API_URL.rstrip("/")
        self._timeout = settings.KG_API_TIMEOUT

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base, timeout=self._timeout)

    @staticmethod
    def _raise(r: httpx.Response) -> None:
        """Raise with the FastAPI detail message when available."""
        if r.is_error:
            try:
                detail = r.json().get("detail", r.text)
            except Exception:
                detail = r.text or r.reason_phrase
            raise RuntimeError(f"Server error {r.status_code}: {detail}")

    async def health(self) -> dict:
        async with self._client() as c:
            r = await c.get("/health")
            self._raise(r)
            return r.json()

    async def query(
        self,
        query: str,
        thread_id: str,
        top_k: int = 10,
        max_hops: int = 2,
    ) -> dict:
        async with self._client() as c:
            r = await c.post(
                "/query",
                json={
                    "query": query,
                    "thread_id": thread_id,
                    "top_k": top_k,
                    "max_hops": max_hops,
                },
            )
            self._raise(r)
            return r.json()

    async def ingest(
        self,
        file_path: str,
        thread_id: str,
        skip_existing: bool = True,
    ) -> dict:
        async with self._client() as c:
            r = await c.post(
                "/ingest",
                json={
                    "file_path": file_path,
                    "thread_id": thread_id,
                    "skip_existing": skip_existing,
                },
            )
            self._raise(r)
            return r.json()

    async def delete_document(self, document_id: str) -> dict:
        async with self._client() as c:
            r = await c.delete(f"/documents/{document_id}")
            self._raise(r)
            return r.json()

    async def list_documents(self, namespace: str) -> dict:
        async with self._client() as c:
            r = await c.get(f"/documents/{namespace}")
            self._raise(r)
            return r.json()

    async def search_node(self, name: str, namespace: str) -> dict:
        async with self._client() as c:
            r = await c.post(
                "/graph/nodes/search",
                json={"name": name, "namespace": namespace},
            )
            self._raise(r)
            return r.json()

    async def traverse(self, node_id: str, max_hops: int = 2) -> dict:
        async with self._client() as c:
            r = await c.post(
                "/graph/traverse",
                json={"node_id": node_id, "max_hops": max_hops},
            )
            self._raise(r)
            return r.json()

    async def cypher(self, query: str, params: dict[str, Any] | None = None) -> dict:
        async with self._client() as c:
            r = await c.post(
                "/graph/cypher",
                json={"query": query, "params": params or {}},
            )
            self._raise(r)
            return r.json()
