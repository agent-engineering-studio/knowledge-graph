"""FastAPI application entrypoint."""

from __future__ import annotations

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import documents, graph, ingest, query
from api.schemas import HealthResponse
from config.settings import settings
from storage.neo4j_graph import Neo4jGraph
from storage.redis_vector import RedisVectorStore
from utils.logger import logger

app = FastAPI(
    title="Knowledge Graph Lab",
    description="Knowledge Graph with vector store, graph database, and RAG pipeline",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(graph.router)
app.include_router(documents.router)


# ── Lifecycle events ─────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup() -> None:
    """Ensure the Redis vector index exists at startup."""
    store = RedisVectorStore()
    await store.create_index()
    logger.info("app_started")


# ── Health check ─────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Check connectivity to Neo4j, Redis, and Ollama."""
    neo4j_ok = False
    redis_ok = False
    ollama_ok = False

    # Neo4j
    try:
        graph = Neo4jGraph()
        await graph.run_cypher("RETURN 1")
        await graph.close()
        neo4j_ok = True
    except Exception as exc:
        logger.warning("health_neo4j_fail", error=str(exc))

    # Redis
    try:
        store = RedisVectorStore()
        await store._client.ping()
        await store.close()
        redis_ok = True
    except Exception as exc:
        logger.warning("health_redis_fail", error=str(exc))

    # Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            ollama_ok = resp.status_code == 200
    except Exception as exc:
        logger.warning("health_ollama_fail", error=str(exc))

    all_ok = neo4j_ok and redis_ok and ollama_ok
    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        neo4j=neo4j_ok,
        redis=redis_ok,
        ollama=ollama_ok,
    )


# ── Delete document ──────────────────────────────────────────────────

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str) -> dict:
    """Delete all chunks belonging to a base document from Redis.

    Args:
        document_id: The base_document_id shared by all chunks of the document.

    Returns:
        Confirmation dict with number of deleted chunks.
    """
    store = RedisVectorStore()
    try:
        chunks_deleted = await store.delete_by_base_id(document_id)
        logger.info("document_deleted", document_id=document_id, chunks=chunks_deleted)
        return {"deleted": document_id, "chunks_deleted": chunks_deleted}
    finally:
        await store.close()
