"""Validator Agent — assesses Knowledge Graph quality and emits a quality report.

The quality metrics (orphan nodes, embedding coverage, etc.) are computed by
running four Cypher queries.  ``compute_quality_report`` is a standalone async
function reused by the Monitor agent.

Uses the Microsoft Agent Framework ``client.as_agent()`` pattern.
"""

from __future__ import annotations

from agent_framework import AgentSession
from pydantic import BaseModel

from agents.client import get_client
from tools.kg_tools import kg_cypher_tool, make_cypher_tools

_VALIDATOR_INSTRUCTIONS = """\
You are a Knowledge Graph quality validator.

## Your task
Run the following four Cypher queries using `run_cypher_query` and compute
quality metrics for the current namespace:

1. Orphan nodes (no connections):
   MATCH (n:KGNode {namespace: $namespace}) WHERE NOT (n)--() RETURN count(n) AS orphan_count

2. Total node count:
   MATCH (n:KGNode {namespace: $namespace}) RETURN count(n) AS node_count

3. Total relation count:
   MATCH (:KGNode {namespace: $namespace})-[r]->(:KGNode) RETURN count(r) AS rel_count

4. Nodes without embeddings:
   MATCH (n:KGNode {namespace: $namespace}) WHERE n.embedding IS NULL RETURN count(n) AS no_embed_count

## Report format
After running all four queries, output a **Quality Report** in this exact format:

**Quality Report — namespace: <namespace>**
- Nodi totali: <node_count>
- Relazioni totali: <rel_count>
- Nodi orfani: <orphan_count>
- Nodi senza embedding: <no_embed_count>
- Grado medio: <rel_count / node_count, 2 decimals>
- Coverage score: <(node_count - no_embed_count) / node_count, as %>
- **Overall health: <composite score, as %>**

Overall health = 50% coverage + 50% (1 - orphan_ratio).
"""


# ── Standalone quality computation (reused by Monitor) ───────────────────────

class KGQualityReport(BaseModel):
    namespace: str
    orphan_nodes: int = 0
    nodes_without_embedding: int = 0
    total_nodes: int = 0
    total_relations: int = 0
    avg_degree: float = 0.0
    coverage_score: float = 0.0
    overall_health: float = 0.0


_ORPHAN_QUERY = "MATCH (n:KGNode {namespace: $namespace}) WHERE NOT (n)--() RETURN count(n) AS orphan_count"
_NODE_COUNT_QUERY = "MATCH (n:KGNode {namespace: $namespace}) RETURN count(n) AS node_count"
_RELATION_COUNT_QUERY = "MATCH (:KGNode {namespace: $namespace})-[r]->(:KGNode) RETURN count(r) AS rel_count"
_NO_EMBED_QUERY = "MATCH (n:KGNode {namespace: $namespace}) WHERE n.embedding IS NULL RETURN count(n) AS no_embed_count"


async def _run_cypher_count(query: str, namespace: str, key: str) -> int:
    try:
        result = await kg_cypher_tool(query=query, namespace=namespace)
        records = result if isinstance(result, list) else result.get("results", [])
        if records:
            return int(records[0].get(key, 0))
    except Exception:
        pass
    return 0


async def compute_quality_report(namespace: str) -> KGQualityReport:
    """Run all quality checks and return a ``KGQualityReport``."""
    orphan_count = await _run_cypher_count(_ORPHAN_QUERY, namespace, "orphan_count")
    node_count = await _run_cypher_count(_NODE_COUNT_QUERY, namespace, "node_count")
    rel_count = await _run_cypher_count(_RELATION_COUNT_QUERY, namespace, "rel_count")
    no_embed_count = await _run_cypher_count(_NO_EMBED_QUERY, namespace, "no_embed_count")

    avg_degree = (rel_count / node_count) if node_count else 0.0
    coverage = 1.0 - (no_embed_count / node_count) if node_count else 0.0
    orphan_penalty = min(1.0, orphan_count / max(node_count, 1))
    overall = max(0.0, coverage * 0.5 + (1 - orphan_penalty) * 0.5)

    return KGQualityReport(
        namespace=namespace,
        orphan_nodes=orphan_count,
        nodes_without_embedding=no_embed_count,
        total_nodes=node_count,
        total_relations=rel_count,
        avg_degree=round(avg_degree, 2),
        coverage_score=round(coverage, 2),
        overall_health=round(overall, 2),
    )


# ── MAF agent ─────────────────────────────────────────────────────────────────

def create_validator_agent(thread_id: str):
    """Create a validator agent for the given namespace/thread."""
    client = get_client()
    tools = make_cypher_tools(thread_id)
    return client.as_agent(
        name="validator",
        instructions=_VALIDATOR_INSTRUCTIONS,
        tools=tools,
    )


async def run_validator(thread_id: str) -> tuple[str, KGQualityReport | None]:
    """Run the validator agent.

    Returns (report_text, quality_report).  Falls back to a structured Cypher
    execution if the agent fails.
    """
    agent = create_validator_agent(thread_id)
    session: AgentSession = agent.create_session()
    session.state["thread_id"] = thread_id

    try:
        output = str(await agent.run("Validate the Knowledge Graph quality", session=session))
    except Exception as exc:
        output = f"Validator Agent failed: {exc}"

    # Also compute the structured report for the API response
    try:
        report = await compute_quality_report(thread_id)
    except Exception:
        report = None

    return output, report
