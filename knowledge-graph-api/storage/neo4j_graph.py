"""Neo4j graph storage using the official async driver."""

from __future__ import annotations

from neo4j import AsyncGraphDatabase

from config.settings import settings
from models.graph_node import GraphNode
from models.relation import Relation, VALID_RELATION_TYPES
from utils.logger import logger


class Neo4jGraph:
    """Async wrapper around Neo4j for knowledge-graph operations."""

    def __init__(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )

    async def close(self) -> None:
        """Close the driver connection."""
        await self._driver.close()

    # ── Node operations ──────────────────────────────────────────────

    async def upsert_node(self, node: GraphNode) -> str:
        """Create or update a knowledge-graph node.

        MERGE is performed on ``{slug, namespace}`` so the same real-world
        entity is never duplicated across ingestion runs.  The UUID ``id`` is
        assigned only on CREATE; existing nodes keep their original UUID.

        Args:
            node: The node to upsert.

        Returns:
            The UUID ``id`` of the upserted node (existing or newly created).
        """
        # source_chunk_ids: append new chunk ids without duplicates
        chunk_id = node.source_chunk_ids[0] if node.source_chunk_ids else None
        query = """
        MERGE (n:KGNode {slug: $slug, namespace: $namespace})
        ON CREATE SET
            n.id = $id,
            n.created_at = $created_at,
            n.source_chunk_ids = $initial_chunks
        ON MATCH SET
            n.source_chunk_ids = CASE
                WHEN $chunk_id IS NOT NULL AND NOT $chunk_id IN coalesce(n.source_chunk_ids, [])
                THEN coalesce(n.source_chunk_ids, []) + [$chunk_id]
                ELSE coalesce(n.source_chunk_ids, [])
            END
        SET n.name = $name,
            n.label = $label,
            n.node_type = $node_type,
            n.importance = $importance,
            n.confidence = $confidence,
            n.description = $description,
            n.updated_at = $updated_at
        RETURN n.id AS node_id
        """
        params = {
            "id": node.id,
            "slug": node.slug or node.id,
            "name": node.name,
            "label": node.label,
            "node_type": node.node_type,
            "namespace": node.namespace,
            "importance": node.importance,
            "confidence": node.confidence,
            "description": node.description,
            "initial_chunks": node.source_chunk_ids,
            "chunk_id": chunk_id,
            "created_at": node.created_at.isoformat(),
            "updated_at": node.updated_at.isoformat(),
        }
        async with self._driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, params)
            record = await result.single()
            node_id: str = record["node_id"]
        logger.debug("node_upserted", node_id=node_id, slug=node.slug, name=node.name)
        return node_id

    async def search_nodes_fuzzy(
        self, query: str, namespace: str, limit: int = 10
    ) -> list[GraphNode]:
        """Case-insensitive substring search for nodes matching any word in *query*.

        Args:
            query: Free-text query (e.g. "mercurio pianeta").
            namespace: Namespace partition.
            limit: Maximum number of nodes to return.

        Returns:
            Nodes ordered by importance descending.
        """
        import re
        words = [w for w in re.sub(r"[^\w\s]", "", query.lower()).split() if len(w) > 2]
        if not words:
            return []
        cypher = """
        MATCH (n:KGNode {namespace: $namespace})
        WHERE ANY(word IN $words WHERE toLower(n.name) CONTAINS word)
        RETURN n
        ORDER BY n.importance DESC
        LIMIT $limit
        """
        results: list[GraphNode] = []
        async with self._driver.session(database=settings.NEO4J_DATABASE) as session:
            cursor = await session.run(
                cypher, {"namespace": namespace, "words": words, "limit": limit}
            )
            async for record in cursor:
                results.append(GraphNode(**dict(record["n"])))
        logger.debug("nodes_fuzzy_found", query=query, count=len(results))
        return results

    async def get_node_by_name(self, name: str, namespace: str) -> GraphNode | None:
        """Lookup a node by name within a namespace.

        Args:
            name: The node name.
            namespace: The namespace partition.

        Returns:
            A ``GraphNode`` or ``None``.
        """
        query = """
        MATCH (n:KGNode {name: $name, namespace: $namespace})
        RETURN n LIMIT 1
        """
        async with self._driver.session(database=settings.NEO4J_DATABASE) as session:
            result = await session.run(query, {"name": name, "namespace": namespace})
            record = await result.single()
            if record is None:
                return None
            props = dict(record["n"])
            return GraphNode(**props)

    async def delete_node(self, node_id: str) -> None:
        """Delete a node and its relationships.

        Args:
            node_id: The unique node id.
        """
        query = "MATCH (n:KGNode {id: $id}) DETACH DELETE n"
        async with self._driver.session(database=settings.NEO4J_DATABASE) as session:
            await session.run(query, {"id": node_id})
        logger.info("node_deleted", node_id=node_id)

    # ── Relation operations ──────────────────────────────────────────

    async def upsert_relation(self, relation: Relation) -> None:
        """Create or update a relation between two nodes.

        The relation type is validated against ``VALID_RELATION_TYPES``
        before being interpolated into the Cypher query.

        Args:
            relation: The relation to upsert.
        """
        if relation.relation_type not in VALID_RELATION_TYPES:
            logger.warning(
                "invalid_relation_type_fallback",
                original=relation.relation_type,
                fallback="RELATES_TO",
            )
            relation = relation.model_copy(update={"relation_type": "RELATES_TO"})

        # source_id / target_id are LLM slugs — match nodes by {slug, namespace}
        query = f"""
        MATCH (a:KGNode {{slug: $source_slug, namespace: $namespace}})
        MATCH (b:KGNode {{slug: $target_slug, namespace: $namespace}})
        MERGE (a)-[r:`{relation.relation_type}` {{id: $id}}]->(b)
        SET r.weight = $weight,
            r.confidence = $confidence,
            r.namespace = $namespace,
            r.properties = $properties
        RETURN r
        """
        params = {
            "id": relation.id,
            "source_slug": relation.source_id,
            "target_slug": relation.target_id,
            "weight": relation.weight,
            "confidence": relation.confidence,
            "namespace": relation.namespace,
            "properties": str(relation.properties),
        }
        async with self._driver.session(database=settings.NEO4J_DATABASE) as session:
            await session.run(query, params)
        logger.debug("relation_upserted", relation_id=relation.id)

    # ── Traversal ────────────────────────────────────────────────────

    async def traverse_neighbors(self, node_id: str, max_hops: int = 2) -> list[dict]:
        """Return neighbors up to *max_hops* from a starting node.

        Args:
            node_id: The starting node id.
            max_hops: Maximum traversal depth.

        Returns:
            A list of dicts with neighbor properties and relationships.
        """
        query = f"""
        MATCH path = (start:KGNode {{id: $node_id}})-[*1..{max_hops}]-(neighbor:KGNode)
        RETURN neighbor, relationships(path) as rels
        LIMIT 50
        """
        results: list[dict] = []
        async with self._driver.session(database=settings.NEO4J_DATABASE) as session:
            cursor = await session.run(query, {"node_id": node_id})
            async for record in cursor:
                results.append({
                    "neighbor": dict(record["neighbor"]),
                    "rels": [dict(r) for r in record["rels"]],
                })
        return results

    async def get_relations_batch(self, node_ids: list[str]) -> list[dict]:
        """Fetch all relations touching a set of nodes.

        Args:
            node_ids: List of node ids.

        Returns:
            List of relation dicts.
        """
        query = """
        MATCH (a:KGNode)-[r]->(b:KGNode)
        WHERE a.id IN $ids OR b.id IN $ids
        RETURN type(r) as type, properties(r) as props, a.id as source, b.id as target
        """
        results: list[dict] = []
        async with self._driver.session(database=settings.NEO4J_DATABASE) as session:
            cursor = await session.run(query, {"ids": node_ids})
            async for record in cursor:
                results.append(dict(record))
        return results

    # ── Raw Cypher ───────────────────────────────────────────────────

    async def run_cypher(self, query: str, params: dict | None = None) -> list[dict]:
        """Execute an arbitrary Cypher query.

        Args:
            query: The Cypher query string.
            params: Optional query parameters.

        Returns:
            List of result records as dicts.
        """
        params = params or {}
        results: list[dict] = []
        async with self._driver.session(database=settings.NEO4J_DATABASE) as session:
            cursor = await session.run(query, params)
            async for record in cursor:
                results.append(dict(record))
        return results
