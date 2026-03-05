"""Graph-augmented RAG pipeline."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator

import httpx
from pydantic import BaseModel

from config.settings import settings
from query.graph_traversal import GraphTraverser
from query.vector_search import VectorSearcher
from utils.logger import logger


class SourceReference(BaseModel):
    """A source chunk referenced in the answer."""

    doc_id: str
    text_preview: str
    score: float | None = None


class QueryOptions(BaseModel):
    """Options for a RAG query."""

    top_k: int = 10
    max_hops: int = 2
    stream: bool = False


class RAGResponse(BaseModel):
    """Structured RAG response."""

    answer: str
    sources: list[SourceReference]
    nodes_used: list[str]
    edges_used: list[str]
    query_intent: str
    processing_time_ms: float


INTENT_PROMPT = """\
Classify the user query into exactly one of these intents:
- document_query: searching for information within documents
- entity_query: looking for a specific entity (person, org, tech, etc.)
- relation_query: asking about relationships between entities
- general: general question not specific to documents or entities

Respond with ONLY the intent label, nothing else.
"""

RAG_SYSTEM_PROMPT = """\
You are a knowledge-graph-augmented assistant.  Answer the user's question
using ONLY the context provided below.  If the context does not contain
enough information, say so honestly.

## Document chunks
{data_text}

## Graph nodes
{nodes_str}

## Graph edges
{edges_str}
"""


class GraphRAGPipeline:
    """Five-stage RAG pipeline: intent → vector search → graph → context → LLM."""

    def __init__(self) -> None:
        self.searcher = VectorSearcher()
        self.traverser = GraphTraverser()

    async def query(
        self,
        user_query: str,
        thread_id: str,
        options: QueryOptions | None = None,
    ) -> RAGResponse | AsyncGenerator[str, None]:
        """Execute a RAG query.

        Args:
            user_query: The natural-language question.
            thread_id: Namespace partition.
            options: Query options.

        Returns:
            A ``RAGResponse`` (non-streaming) or an async generator of
            string chunks (streaming).
        """
        options = options or QueryOptions()
        start = time.perf_counter()

        # 1 — Intent analysis
        intent = await self._classify_intent(user_query)
        logger.info("query_intent", intent=intent)

        # 2 — Vector search
        docs = await self.searcher.search(user_query, top_k=options.top_k, namespace=thread_id)
        data_text = "\n\n---\n\n".join(d.text for d in docs)
        sources = [
            SourceReference(doc_id=d.id, text_preview=d.text[:200])
            for d in docs
        ]

        # 3 — Graph enrichment
        # Extract entity ids mentioned in top chunks (heuristic: look up by name)
        node_ids: list[str] = []
        graph_data = await self.traverser.enrich(node_ids, max_hops=options.max_hops)
        nodes_str = json.dumps(graph_data["nodes"], default=str) if graph_data["nodes"] else "None"
        edges_str = json.dumps(graph_data["edges"], default=str) if graph_data["edges"] else "None"

        # 4 — Context assembly
        system_message = RAG_SYSTEM_PROMPT.format(
            data_text=data_text or "No relevant documents found.",
            nodes_str=nodes_str,
            edges_str=edges_str,
        )

        # 5 — LLM generation
        if options.stream:
            return self._stream_response(system_message, user_query)

        answer = await self._generate(system_message, user_query)
        elapsed_ms = (time.perf_counter() - start) * 1000

        return RAGResponse(
            answer=answer,
            sources=sources,
            nodes_used=[n.get("neighbor", {}).get("id", "") for n in graph_data["nodes"]],
            edges_used=[str(e) for e in graph_data["edges"]],
            query_intent=intent,
            processing_time_ms=round(elapsed_ms, 1),
        )

    # ── Private helpers ──────────────────────────────────────────────

    async def _classify_intent(self, query: str) -> str:
        """Use Ollama to classify the query intent."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": settings.OLLAMA_LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": INTENT_PROMPT},
                        {"role": "user", "content": query},
                    ],
                    "stream": False,
                },
            )
            response.raise_for_status()
            raw = response.json()["message"]["content"].strip().lower()
        valid = {"document_query", "entity_query", "relation_query", "general"}
        return raw if raw in valid else "general"

    async def _generate(self, system_message: str, user_query: str) -> str:
        """Non-streaming LLM generation."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": settings.OLLAMA_LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_query},
                    ],
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["message"]["content"]

    async def _stream_response(
        self, system_message: str, user_query: str
    ) -> AsyncGenerator[str, None]:
        """Streaming LLM generation via SSE-compatible chunks."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": settings.OLLAMA_LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_query},
                    ],
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
