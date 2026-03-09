"""Graph-augmented RAG pipeline."""

from __future__ import annotations

import asyncio
import json
import os
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
    page_number: int | None = None
    total_pages: int | None = None
    document_name: str | None = None


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


# Keywords used for fast (no-LLM) intent classification
_RELATION_KEYWORDS = {
    "relazione", "collegamento", "relation", "relationship", "connected",
    "connesso", "connessi", "link", "between", "tra", "dipende", "depends",
    "influenza", "influenced", "associato", "associated",
}
_ENTITY_KEYWORDS = {
    "chi è", "who is", "cos'è", "cosa è", "what is", "describe",
    "descrivi", "entity", "entità", "persona", "person", "organizzazione",
    "organization", "definisci", "define", "tell me about",
}

RAG_SYSTEM_PROMPT = """\
You are a knowledge-graph-augmented assistant. Your ONLY source of information \
is the context provided below. You MUST NOT use any knowledge from your training data.

Rules:
- Answer ONLY using the document chunks and graph data provided.
- If the context does not contain the answer, say exactly: \
"The provided documents do not contain information about this topic."
- Do NOT invent, infer, or supplement with external knowledge.
- Cite which chunk(s) support your answer when possible.
- Answer in the same language as the user's question.

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

        # 1 — Intent analysis (keyword-based, no LLM round-trip)
        t1 = time.perf_counter()
        intent = self._classify_intent(user_query)
        logger.info("query_intent", intent=intent, ms=round((time.perf_counter() - t1) * 1000, 1))

        # 2 — Hybrid retrieval: vector search + keyword search in parallel
        t2 = time.perf_counter()
        vector_task = self.searcher.search(user_query, top_k=options.top_k, namespace=thread_id)
        keyword_task = self.searcher.keyword_search(user_query, namespace=thread_id, top_k=5)
        vector_docs, keyword_docs = await asyncio.gather(vector_task, keyword_task)

        # Merge: keyword hits first (exact match → higher relevance), deduplicate
        seen_ids: set[str] = set()
        docs: list = []
        for d in keyword_docs:
            if d.id not in seen_ids:
                docs.append(d)
                seen_ids.add(d.id)
        for d in vector_docs:
            if d.id not in seen_ids:
                docs.append(d)
                seen_ids.add(d.id)

        logger.info(
            "hybrid_retrieval_done",
            keyword=len(keyword_docs),
            vector=len(vector_docs),
            merged=len(docs),
            ms=round((time.perf_counter() - t2) * 1000, 1),
        )

        # 3 — Graph enrichment from chunk node_ids (bidirectional reference)
        t3 = time.perf_counter()
        # Collect unique node_ids from all retrieved chunks
        node_ids: list[str] = list(
            dict.fromkeys(nid for d in docs for nid in (d.node_ids or []))
        )

        # For entity/relation queries also search Neo4j by name as fallback
        # (covers docs ingested before node_ids were tracked)
        if intent in ("entity_query", "relation_query") and not node_ids:
            entity_nodes = await self.traverser.find_entities(user_query, thread_id)
            node_ids = [n.id for n in entity_nodes]
            logger.info("entity_nodes_fallback", count=len(node_ids), names=[n.name for n in entity_nodes])

        logger.info("graph_node_ids_collected", count=len(node_ids), intent=intent)
        graph_data = await self.traverser.enrich(node_ids, max_hops=options.max_hops)
        logger.info(
            "graph_enrichment_done",
            nodes=len(graph_data["nodes"]),
            edges=len(graph_data["edges"]),
            ms=round((time.perf_counter() - t3) * 1000, 1),
        )

        data_text = "\n\n---\n\n".join(d.text for d in docs)
        sources = [
            SourceReference(
                doc_id=d.id,
                text_preview=d.text[:200],
                page_number=d.page_number,
                total_pages=d.total_pages if d.total_pages else None,
                document_name=os.path.basename(d.name) if d.name else None,
            )
            for d in docs
        ]
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

    def _classify_intent(self, query: str) -> str:
        """Classify query intent using fast keyword matching (no LLM round-trip)."""
        q = query.lower()
        if any(kw in q for kw in _RELATION_KEYWORDS):
            return "relation_query"
        if any(kw in q for kw in _ENTITY_KEYWORDS):
            return "entity_query"
        return "document_query"

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
        logger.info("llm_stream_start", model=settings.OLLAMA_LLM_MODEL)
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
                logger.info("llm_stream_connected", status=response.status_code)
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("stream_invalid_json", line=line[:200])
                        continue
                    if data.get("error"):
                        logger.error("llm_stream_error", error=data["error"])
                        raise RuntimeError(f"Ollama error: {data['error']}")
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        logger.info("llm_stream_done")
