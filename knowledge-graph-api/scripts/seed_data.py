"""Seed the knowledge graph with example documents."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from pipeline.ingest import IngestionPipeline, IngestOptions
from utils.logger import logger

SAMPLE_DOCS = [
    {
        "name": "redis_overview.txt",
        "content": (
            "Redis is an open-source, in-memory data structure store used as a database, "
            "cache, and message broker. Redis supports data structures such as strings, "
            "hashes, lists, sets, sorted sets with range queries, bitmaps, hyperloglogs, "
            "geospatial indexes, and streams. Redis has built-in replication, Lua scripting, "
            "LRU eviction, transactions, and different levels of on-disk persistence.\n\n"
            "Redis Sentinel provides high availability. Redis Cluster provides automatic "
            "partitioning across multiple Redis nodes. RedisSearch adds full-text search "
            "and vector similarity search capabilities."
        ),
    },
    {
        "name": "neo4j_overview.txt",
        "content": (
            "Neo4j is a graph database management system developed by Neo4j, Inc. "
            "It stores data as nodes and relationships instead of traditional tables. "
            "Neo4j uses the Cypher query language, which is designed to be intuitive and "
            "expressive for graph pattern matching.\n\n"
            "Neo4j is widely used for fraud detection, recommendation engines, "
            "knowledge graphs, network management, and identity and access management. "
            "The APOC library extends Neo4j with hundreds of useful procedures and functions."
        ),
    },
    {
        "name": "ollama_overview.txt",
        "content": (
            "Ollama is a tool for running large language models locally. "
            "It supports popular models like Llama 3, Mistral, Gemma, and many others. "
            "Ollama provides a simple HTTP API for inference, making it easy to integrate "
            "with applications.\n\n"
            "The nomic-embed-text model generates 768-dimensional embeddings and is "
            "optimized for semantic search and retrieval-augmented generation (RAG) pipelines. "
            "Ollama runs efficiently on consumer hardware with GPU acceleration support."
        ),
    },
]


async def main() -> None:
    """Create temp files and run the ingestion pipeline."""
    pipeline = IngestionPipeline()
    thread_id = "seed"

    for doc in SAMPLE_DOCS:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", encoding="utf-8", delete=False) as fh:
            fh.write(doc["content"])
            tmp = Path(fh.name)

        logger.info("seeding", name=doc["name"])
        try:
            result = await pipeline.ingest(
                file_path=str(tmp),
                thread_id=thread_id,
                options=IngestOptions(skip_existing=True),
            )
            logger.info(
                "seed_result",
                name=doc["name"],
                chunks=result.chunks_processed,
                entities=result.entities_extracted,
                relations=result.relations_extracted,
                nodes=result.nodes_created,
                edges=result.edges_created,
            )
        finally:
            tmp.unlink(missing_ok=True)

    logger.info("seeding_complete")


if __name__ == "__main__":
    asyncio.run(main())
