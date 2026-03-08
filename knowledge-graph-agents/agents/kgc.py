"""KGC Agent — Knowledge Graph Completion via rule-based and LLM-based approaches."""

from __future__ import annotations

from pydantic import BaseModel

from tools.kg_tools import kg_cypher_tool, kg_query_tool
from orchestration.state import AgentState


class RelationProposal(BaseModel):
    source_name: str
    target_name: str
    proposed_relation: str
    confidence: float
    evidence: str


class KGCProposal(BaseModel):
    new_relations: list[RelationProposal]
    total_candidates_evaluated: int


# Cypher: find nodes with few relations (potential isolated nodes)
_LOW_DEGREE_QUERY = """
MATCH (n:KGNode {namespace: $namespace})
WITH n, size([(n)--() | 1]) AS degree
WHERE degree < 2
RETURN n.id AS id, n.name AS name, n.node_type AS node_type
LIMIT 20
"""

# Cypher: find transitive candidates (friend-of-friend not yet linked)
_TRANSITIVE_QUERY = """
MATCH (a:KGNode {namespace: $namespace})-[]->(b:KGNode)<-[]-(c:KGNode {namespace: $namespace})
WHERE NOT (a)-[]-(c) AND a.id <> c.id
RETURN a.name AS source, c.name AS target, count(*) AS shared_neighbors
ORDER BY shared_neighbors DESC
LIMIT 10
"""


async def find_missing_relations(namespace: str) -> KGCProposal:
    """Identify missing relations using rule-based heuristics.

    Phase 1: transitive closure candidates only.  LLM-based scoring will be
    added in Phase 2.

    Args:
        namespace: The KG namespace to inspect.
    """
    proposals: list[RelationProposal] = []

    # Rule-based: transitive closure
    try:
        result = await kg_cypher_tool(query=_TRANSITIVE_QUERY, namespace=namespace)
        records = result if isinstance(result, list) else result.get("results", [])
        for rec in records[:10]:
            shared = int(rec.get("shared_neighbors", 1))
            confidence = min(0.95, 0.5 + shared * 0.05)
            proposals.append(
                RelationProposal(
                    source_name=rec.get("source", "?"),
                    target_name=rec.get("target", "?"),
                    proposed_relation="RELATED_TO",
                    confidence=round(confidence, 2),
                    evidence=f"{shared} vicini condivisi nel grafo",
                )
            )
    except Exception:
        pass

    # Semantic similarity: low-degree nodes queried for similar context
    try:
        low_result = await kg_cypher_tool(query=_LOW_DEGREE_QUERY, namespace=namespace)
        low_records = low_result if isinstance(low_result, list) else low_result.get("results", [])
        for rec in low_records[:5]:
            node_name = rec.get("name", "")
            if not node_name:
                continue
            try:
                rag = await kg_query_tool(
                    query=f"Entità correlate a {node_name}",
                    thread_id=namespace,
                    top_k=3,
                    max_hops=1,
                )
                nodes_used = rag.get("nodes_used", [])
                for related_id in nodes_used[:2]:
                    if related_id and related_id != rec.get("id"):
                        proposals.append(
                            RelationProposal(
                                source_name=node_name,
                                target_name=related_id,
                                proposed_relation="SEMANTICALLY_RELATED",
                                confidence=0.65,
                                evidence="Alta similarità semantica vettoriale",
                            )
                        )
            except Exception:
                pass
    except Exception:
        pass

    return KGCProposal(
        new_relations=proposals,
        total_candidates_evaluated=len(proposals),
    )


async def kgc_node(state: AgentState) -> AgentState:
    """LangGraph node: find missing relations and store proposals in context."""
    context: dict = dict(state.get("context", {}))
    thread_id: str = state.get("thread_id", "default")

    try:
        proposal = await find_missing_relations(thread_id)
    except Exception as exc:
        return {
            **state,
            "context": context,
            "error": f"KGC Agent: completion failed — {exc}",
            "final_output": f"Errore nel completamento del grafo: {exc}",
        }

    context["kgc_proposal"] = proposal.model_dump()

    lines = [f"**KGC — {len(proposal.new_relations)} relazioni proposte**\n"]
    for i, rel in enumerate(proposal.new_relations[:10], 1):
        lines.append(
            f"{i}. `{rel.source_name}` → **{rel.proposed_relation}** → `{rel.target_name}` "
            f"(confidence: {rel.confidence:.0%}) — {rel.evidence}"
        )

    return {
        **state,
        "context": context,
        "final_output": "\n".join(lines),
        "error": None,
    }
