"""Graph traversal helpers for the RAG pipeline."""

from __future__ import annotations

from storage.neo4j_graph import Neo4jGraph


class GraphTraverser:
    """Convenience wrapper for graph neighbourhood lookups."""

    def __init__(self) -> None:
        self.graph = Neo4jGraph()

    async def enrich(self, node_ids: list[str], max_hops: int = 2) -> dict:
        """Traverse neighbours and fetch relations for a set of nodes.

        Args:
            node_ids: Starting node ids.
            max_hops: Traversal depth.

        Returns:
            Dict with ``nodes`` and ``edges`` lists.
        """
        all_neighbors: list[dict] = []
        for nid in node_ids:
            neighbors = await self.graph.traverse_neighbors(nid, max_hops=max_hops)
            all_neighbors.extend(neighbors)

        edges = await self.graph.get_relations_batch(node_ids)

        return {
            "nodes": all_neighbors,
            "edges": edges,
        }
