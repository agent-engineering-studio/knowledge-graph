"""Validator Agent — assesses Knowledge Graph quality and emits a quality report."""

from __future__ import annotations

from pydantic import BaseModel

from tools.kg_tools import kg_cypher_tool
from orchestration.state import AgentState


class KGQualityReport(BaseModel):
    """Quality metrics for a KG namespace."""

    namespace: str
    orphan_nodes: int = 0
    nodes_without_embedding: int = 0
    total_nodes: int = 0
    total_relations: int = 0
    avg_degree: float = 0.0
    coverage_score: float = 0.0   # % nodes with embeddings
    overall_health: float = 0.0   # composite 0.0 → 1.0


_ORPHAN_QUERY = """
MATCH (n:KGNode {namespace: $namespace})
WHERE NOT (n)--()
RETURN count(n) AS orphan_count
"""

_NODE_COUNT_QUERY = """
MATCH (n:KGNode {namespace: $namespace})
RETURN count(n) AS node_count
"""

_RELATION_COUNT_QUERY = """
MATCH (:KGNode {namespace: $namespace})-[r]->(:KGNode)
RETURN count(r) AS rel_count
"""

_NO_EMBED_QUERY = """
MATCH (n:KGNode {namespace: $namespace})
WHERE n.embedding IS NULL
RETURN count(n) AS no_embed_count
"""


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
    """Run all quality checks and return a ``KGQualityReport``.

    Args:
        namespace: The KG namespace (thread_id) to inspect.
    """
    orphan_count = await _run_cypher_count(_ORPHAN_QUERY, namespace, "orphan_count")
    node_count = await _run_cypher_count(_NODE_COUNT_QUERY, namespace, "node_count")
    rel_count = await _run_cypher_count(_RELATION_COUNT_QUERY, namespace, "rel_count")
    no_embed_count = await _run_cypher_count(_NO_EMBED_QUERY, namespace, "no_embed_count")

    avg_degree = (rel_count / node_count) if node_count else 0.0
    coverage = 1.0 - (no_embed_count / node_count) if node_count else 0.0

    # Composite health: penalise orphans and missing embeddings
    orphan_penalty = min(1.0, orphan_count / max(node_count, 1))
    overall = max(0.0, (coverage * 0.5 + (1 - orphan_penalty) * 0.5))

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


async def validator_node(state: AgentState) -> AgentState:
    """LangGraph node: compute quality report and store in context."""
    context: dict = dict(state.get("context", {}))
    thread_id: str = state.get("thread_id", "default")

    try:
        report = await compute_quality_report(thread_id)
    except Exception as exc:
        return {
            **state,
            "context": context,
            "error": f"Validator Agent: quality check failed — {exc}",
            "final_output": state.get("final_output", ""),
        }

    context["quality_report"] = report.model_dump()

    quality_summary = (
        f"**Quality Report — namespace: {thread_id}**\n"
        f"- Nodi totali: {report.total_nodes}\n"
        f"- Relazioni totali: {report.total_relations}\n"
        f"- Nodi orfani: {report.orphan_nodes}\n"
        f"- Nodi senza embedding: {report.nodes_without_embedding}\n"
        f"- Grado medio: {report.avg_degree}\n"
        f"- Coverage score: {report.coverage_score:.0%}\n"
        f"- **Overall health: {report.overall_health:.0%}**"
    )

    # Append quality info after any previous output (e.g. ingestion summary)
    previous_output = state.get("final_output") or ""
    final = (previous_output + "\n\n" + quality_summary).strip()

    return {
        **state,
        "context": context,
        "final_output": final,
        "error": None,
    }
