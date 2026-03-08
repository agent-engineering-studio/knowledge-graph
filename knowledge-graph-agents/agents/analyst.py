"""Analyst Agent — answers questions using vector search, graph traversal, or both."""

from __future__ import annotations

from tools.kg_tools import kg_query_tool, kg_search_nodes_tool, kg_traverse_tool
from orchestration.state import AgentState


async def _vector_search(query: str, thread_id: str, top_k: int = 10) -> dict:
    """Pure vector semantic search via RAG pipeline."""
    return await kg_query_tool(query=query, thread_id=thread_id, top_k=top_k, max_hops=0)


async def _graph_traversal(query: str, thread_id: str) -> dict:
    """Structural graph traversal: look up the entity then explore neighbours."""
    # Step 1: find the main entity node by name (use query as entity name hint)
    node_result = await kg_search_nodes_tool(name=query, namespace=thread_id)
    node = node_result.get("node")
    if not node:
        return {"answer": "Nessun nodo trovato per l'entità richiesta.", "graph_path": []}

    # Step 2: traverse from the found node
    node_id = node.get("id", "")
    traversal = await kg_traverse_tool(node_id=node_id, max_hops=2)

    neighbors = traversal.get("nodes", [])
    edges = traversal.get("edges", [])

    graph_path = [
        f"{node.get('name', '')} → {e.get('type', '?')} → {e.get('target', '')}"
        for e in edges[:10]
    ]

    answer = (
        f"Entità principale: {node.get('name')} (tipo: {node.get('node_type', '?')})\n"
        f"Vicini trovati: {len(neighbors)}\n"
        f"Relazioni: {len(edges)}"
    )

    return {
        "answer": answer,
        "graph_path": graph_path,
        "node": node,
        "neighbors": neighbors,
    }


async def _hybrid_search(query: str, thread_id: str, top_k: int = 10) -> dict:
    """Combine vector search and graph traversal results."""
    vector_result = await _vector_search(query, thread_id, top_k)

    # Try graph traversal only when a node is explicitly mentioned
    graph_result: dict = {}
    try:
        graph_result = await _graph_traversal(query, thread_id)
    except Exception:
        graph_result = {"answer": "", "graph_path": []}

    # Merge: use the RAG answer as primary, enrich with graph path
    combined_answer = vector_result.get("answer", "")
    graph_path = graph_result.get("graph_path", [])
    if graph_path:
        combined_answer += "\n\n**Percorso nel grafo:**\n" + "\n".join(graph_path)

    sources = vector_result.get("sources", [])
    confidence = min(1.0, len(sources) / 5) if sources else 0.3

    return {
        "answer": combined_answer,
        "confidence": confidence,
        "sources": sources,
        "graph_path": graph_path,
        "nodes_used": vector_result.get("nodes_used", []),
        "edges_used": vector_result.get("edges_used", []),
        "query_intent": vector_result.get("query_intent", "general"),
    }


async def analyst_node(state: AgentState) -> AgentState:
    """LangGraph node: answer the user query using the appropriate search strategy.

    Strategy is read from ``context["analyst_strategy"]`` if present, else
    defaults to ``"hybrid"``.
    """
    context: dict = dict(state.get("context", {}))
    thread_id: str = state.get("thread_id", "default")
    query: str = context.get("query", state.get("user_request", ""))
    strategy: str = context.get("analyst_strategy", "hybrid")
    top_k: int = context.get("top_k", 10)

    try:
        if strategy == "vector":
            result = await _vector_search(query, thread_id, top_k)
        elif strategy == "graph":
            result = await _graph_traversal(query, thread_id)
        else:
            result = await _hybrid_search(query, thread_id, top_k)
    except Exception as exc:
        return {
            **state,
            "context": context,
            "error": f"Analyst Agent: search failed — {exc}",
            "final_output": f"Errore durante la ricerca: {exc}",
        }

    context["analyst_result"] = result

    return {
        **state,
        "context": context,
        "final_output": result.get("answer", "Nessuna risposta trovata."),
        "error": None,
    }
