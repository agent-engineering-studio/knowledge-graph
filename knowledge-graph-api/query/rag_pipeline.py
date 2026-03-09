"""Graph-augmented retrieval pipeline (no LLM generation)."""

from __future__ import annotations

import asyncio
import os
import time

from pydantic import BaseModel

from query.graph_traversal import GraphTraverser
from query.vector_search import VectorSearcher
from utils.logger import logger


class SourceReference(BaseModel):
    """A source chunk returned by the retrieval."""

    doc_id: str
    text_preview: str
    score: float | None = None
    page_number: int | None = None
    total_pages: int | None = None
    document_name: str | None = None


class QueryOptions(BaseModel):
    """Options for a retrieval query."""

    top_k: int = 10
    max_hops: int = 2


class RAGResponse(BaseModel):
    """Structured retrieval response (semantic search + graph, no LLM)."""

    answer: str
    sources: list[SourceReference]
    nodes_used: list[str]
    edges_used: list[str]
    graph_context: str
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

_NO_DOCS_REPLY = {
    "it": "I documenti forniti non contengono informazioni su questo argomento.",
    "en": "The provided documents do not contain information about this topic.",
}


def _no_docs_message(query: str) -> str:
    """Return the 'no documents' message in the appropriate language."""
    q = query.lower()
    if any(w in q for w in ("cosa", "che", "come", "quale", "quanto", "chi", "dove", "quando", "dammi", "dimmi")):
        return _NO_DOCS_REPLY["it"]
    return _NO_DOCS_REPLY["en"]


def _format_node(props: dict) -> str:
    """Format a graph node as a human-readable string."""
    name = props.get("name") or props.get("id", "Unknown")
    node_type = props.get("node_type", "")
    description = props.get("description", "")
    line = name
    if node_type:
        line += f" [{node_type}]"
    if description:
        line += f" - {description}"
    return line


def _format_edge(edge: dict, node_map: dict[str, str]) -> str:
    """Format a graph edge as a human-readable triple."""
    src = node_map.get(edge.get("source", ""), edge.get("source", "?"))
    tgt = node_map.get(edge.get("target", ""), edge.get("target", "?"))
    rel = edge.get("type", "RELATES_TO")
    props = edge.get("props") or {}
    weight = props.get("weight")
    confidence = props.get("confidence")
    extra = ""
    if weight is not None or confidence is not None:
        parts = []
        if weight is not None:
            parts.append(f"w:{weight}")
        if confidence is not None:
            parts.append(f"c:{confidence}")
        extra = f" ({', '.join(parts)})"
    return f"{src} --[{rel}]--> {tgt}{extra}"


def _build_graph_strings(graph_data: dict) -> tuple[str, str, list[str], list[str]]:
    """Build human-readable strings from raw graph traversal data."""
    node_map: dict[str, str] = {}
    for item in graph_data["nodes"]:
        neighbor = item["neighbor"]
        nid = neighbor.get("id", "")
        name = neighbor.get("name") or nid
        if nid:
            node_map[nid] = name

    seen: set[str] = set()
    nodes_list: list[str] = []
    for item in graph_data["nodes"]:
        neighbor = item["neighbor"]
        nid = neighbor.get("id", "")
        if nid in seen:
            continue
        seen.add(nid)
        nodes_list.append(_format_node(neighbor))

    nodes_str = "\n".join(nodes_list) if nodes_list else "None"

    edges_list = [_format_edge(e, node_map) for e in graph_data["edges"]]
    edges_str = "\n".join(edges_list) if edges_list else "None"

    return nodes_str, edges_str, nodes_list, edges_list


def _build_answer(
    docs: list,
    nodes_list: list[str],
    edges_list: list[str],
    user_query: str,
) -> str:
    """Build the structured answer text from retrieved data (no LLM)."""
    if not docs and not nodes_list:
        return _no_docs_message(user_query)

    parts: list[str] = []

    if docs:
        parts.append("## Risultati ricerca semantica\n")
        for d in docs:
            label = os.path.basename(d.name) if d.name else d.id
            page_info = ""
            if d.page_number is not None:
                total = f"/{d.total_pages}" if d.total_pages else ""
                page_info = f" (p.{d.page_number + 1}{total})"
            parts.append(f"**[{label}{page_info}]**\n{d.text}\n")

    if nodes_list:
        parts.append("## Nodi del grafo\n")
        for node in nodes_list:
            parts.append(f"- {node}")

    if edges_list:
        parts.append("\n## Relazioni\n")
        for edge in edges_list:
            parts.append(f"- {edge}")

    return "\n".join(parts)


class GraphRAGPipeline:
    """Retrieval pipeline: intent → vector search → graph enrichment → structured answer."""

    def __init__(self) -> None:
        self.searcher = VectorSearcher()
        self.traverser = GraphTraverser()

    async def query(
        self,
        user_query: str,
        thread_id: str,
        options: QueryOptions | None = None,
    ) -> RAGResponse:
        """Execute a retrieval query and return structured results (no LLM).

        Args:
            user_query: The natural-language question.
            thread_id: Namespace partition.
            options: Query options.

        Returns:
            A ``RAGResponse`` with documents, graph nodes, and relationships.
        """
        options = options or QueryOptions()
        start = time.perf_counter()

        # 1 — Intent classification (keyword-based, no LLM)
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

        # 3 — Graph enrichment from chunk node_ids
        t3 = time.perf_counter()
        node_ids: list[str] = list(
            dict.fromkeys(nid for d in docs for nid in (d.node_ids or []))
        )

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

        # 4 — Format graph data
        nodes_str, edges_str, nodes_list, edges_list = _build_graph_strings(graph_data)
        graph_context = "### Nodes\n" + nodes_str + "\n\n### Relationships\n" + edges_str

        # 5 — Build sources list
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

        # 6 — Build structured answer directly from retrieved data (no LLM)
        answer = _build_answer(docs, nodes_list, edges_list, user_query)

        elapsed_ms = (time.perf_counter() - start) * 1000
        return RAGResponse(
            answer=answer,
            sources=sources,
            nodes_used=nodes_list,
            edges_used=edges_list,
            graph_context=graph_context,
            query_intent=intent,
            processing_time_ms=round(elapsed_ms, 1),
        )

    def _classify_intent(self, query: str) -> str:
        """Classify query intent using fast keyword matching (no LLM round-trip)."""
        q = query.lower()
        if any(kw in q for kw in _RELATION_KEYWORDS):
            return "relation_query"
        if any(kw in q for kw in _ENTITY_KEYWORDS):
            return "entity_query"
        return "document_query"
