"""KGC Agent — Knowledge Graph Completion via transitive closure and semantic similarity.

Uses the Microsoft Agent Framework ``client.as_agent()`` + ``AgentSession`` pattern.

Relation candidates are identified explicitly in Python (Cypher queries + semantic
similarity) rather than via LLM tool-calling.  The MAF agent formats the proposals
into a readable report.
"""

from __future__ import annotations

from agent_framework import AgentSession
from pydantic import BaseModel

from agents.client import get_client
from tools.kg_tools import kg_cypher_tool, kg_query_tool

_KGC_INSTRUCTIONS = """\
You are a Knowledge Graph Completion specialist.

## Your task
The user message contains candidate missing relations found by automated analysis.
Format them into a clear report:

**KGC — <N> relazioni proposte**

For each proposal:
<N>. `<source>` → **<RELATION>** → `<target>` (confidence: <X>%) — <evidence>

Then summarise: which relations look most promising, and why.
"""


class RelationProposal(BaseModel):
    source_name: str
    target_name: str
    proposed_relation: str
    confidence: float
    evidence: str


class KGCProposal(BaseModel):
    new_relations: list[RelationProposal]
    total_candidates_evaluated: int


_TRANSITIVE_QUERY = """
MATCH (a:KGNode {namespace: $namespace})-[]->(b:KGNode)<-[]-(c:KGNode {namespace: $namespace})
WHERE NOT (a)-[]-(c) AND a.id <> c.id
RETURN a.name AS source, c.name AS target, count(*) AS shared_neighbors
ORDER BY shared_neighbors DESC
LIMIT 10
"""

_LOW_DEGREE_QUERY = """
MATCH (n:KGNode {namespace: $namespace})
WITH n, size([(n)--() | 1]) AS degree
WHERE degree < 2
RETURN n.id AS id, n.name AS name, n.node_type AS node_type
LIMIT 10
"""


async def find_missing_relations(namespace: str) -> KGCProposal:
    """Identify missing relations using rule-based heuristics (no LLM)."""
    proposals: list[RelationProposal] = []

    # Strategy 1: transitive closure
    try:
        result = await kg_cypher_tool(query=_TRANSITIVE_QUERY, namespace=namespace)
        records = result if isinstance(result, list) else result.get("results", [])
        for rec in records[:10]:
            shared = int(rec.get("shared_neighbors", 1))
            confidence = min(0.95, 0.5 + shared * 0.05)
            proposals.append(RelationProposal(
                source_name=rec.get("source", "?"),
                target_name=rec.get("target", "?"),
                proposed_relation="RELATED_TO",
                confidence=round(confidence, 2),
                evidence=f"{shared} vicini condivisi nel grafo",
            ))
    except Exception:
        pass

    # Strategy 2: semantic similarity for low-degree nodes
    try:
        low_result = await kg_cypher_tool(query=_LOW_DEGREE_QUERY, namespace=namespace)
        low_records = low_result if isinstance(low_result, list) else low_result.get("results", [])
        for rec in low_records[:5]:
            node_name = rec.get("name", "")
            if not node_name:
                continue
            try:
                rag = await kg_query_tool(
                    query=f"Entità correlate a {node_name}", thread_id=namespace, top_k=3, max_hops=1
                )
                for related_id in rag.get("nodes_used", [])[:2]:
                    if related_id and related_id != rec.get("id"):
                        proposals.append(RelationProposal(
                            source_name=node_name,
                            target_name=related_id,
                            proposed_relation="SEMANTICALLY_RELATED",
                            confidence=0.65,
                            evidence="Alta similarità semantica vettoriale",
                        ))
            except Exception:
                pass
    except Exception:
        pass

    return KGCProposal(new_relations=proposals, total_candidates_evaluated=len(proposals))


def create_kgc_agent(thread_id: str):
    """Create a KGC agent (no tools — proposals injected in prompt)."""
    client = get_client()
    return client.as_agent(
        name="kgc",
        instructions=_KGC_INSTRUCTIONS,
    )


async def run_kgc(request: str, thread_id: str) -> str:
    """Find missing relations in Python, then format them via the MAF agent."""
    proposal = await find_missing_relations(thread_id)

    if not proposal.new_relations:
        return "**KGC — nessuna relazione mancante identificata** per questo namespace."

    lines = [f"**KGC — {len(proposal.new_relations)} relazioni proposte**\n"]
    for i, rel in enumerate(proposal.new_relations[:10], 1):
        lines.append(
            f"{i}. `{rel.source_name}` → **{rel.proposed_relation}** → `{rel.target_name}` "
            f"(confidence: {rel.confidence:.0%}) — {rel.evidence}"
        )

    proposals_text = "\n".join(lines)
    prompt = f"<proposals>\n{proposals_text}\n</proposals>\n\nFormatting request: {request}"

    agent = create_kgc_agent(thread_id)
    session: AgentSession = agent.create_session()
    session.state["thread_id"] = thread_id

    try:
        return str(await agent.run(prompt, session=session))
    except Exception:
        return proposals_text  # fallback: return raw proposals
