"""Graph exploration routes."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from storage.neo4j_graph import Neo4jGraph
from utils.logger import logger

router = APIRouter(prefix="/graph", tags=["graph"])

# ── Cypher guardrail ────────────────────────────────────────────────

_WRITE_PATTERN = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|CALL\s*\{)\b",
    re.IGNORECASE,
)


class CypherRequest(BaseModel):
    """Body for POST /graph/cypher."""

    query: str
    params: dict | None = None


class SearchNodeRequest(BaseModel):
    """Body for POST /graph/nodes/search."""

    name: str
    namespace: str


class TraverseRequest(BaseModel):
    """Body for POST /graph/traverse."""

    node_id: str
    max_hops: int = 2


# ── Endpoints ───────────────────────────────────────────────────────


@router.post("/nodes/search")
async def search_node(body: SearchNodeRequest) -> dict:
    """Find a node by name within a namespace.

    Returns:
        The node properties or null.
    """
    graph = Neo4jGraph()
    try:
        node = await graph.get_node_by_name(body.name, body.namespace)
        return {"node": node.model_dump(mode="json") if node else None}
    finally:
        await graph.close()


@router.post("/traverse")
async def traverse(body: TraverseRequest) -> dict:
    """Traverse neighbours of a node up to max_hops.

    Returns:
        Dict with nodes and edges lists.
    """
    graph = Neo4jGraph()
    try:
        neighbors = await graph.traverse_neighbors(body.node_id, max_hops=body.max_hops)
        edges = await graph.get_relations_batch([body.node_id])
        return {"nodes": neighbors, "edges": edges}
    finally:
        await graph.close()


@router.post("/cypher")
async def run_cypher(body: CypherRequest) -> dict:
    """Execute a read-only Cypher query.

    Write operations (CREATE, MERGE, DELETE, SET, REMOVE, DROP) are rejected.

    Returns:
        List of result records.
    """
    if _WRITE_PATTERN.search(body.query):
        raise HTTPException(
            status_code=400,
            detail="Write operations are not allowed via this endpoint.",
        )
    graph = Neo4jGraph()
    try:
        records = await graph.run_cypher(body.query, body.params)
        return {"records": records}
    except Exception as exc:
        logger.error("cypher_error", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        await graph.close()
