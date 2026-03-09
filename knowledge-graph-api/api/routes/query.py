"""Query routes — retrieval only (no LLM generation)."""

from __future__ import annotations

import traceback

from fastapi import APIRouter, HTTPException

from api.schemas import QueryRequest
from query.rag_pipeline import GraphRAGPipeline, QueryOptions, RAGResponse
from utils.logger import logger

router = APIRouter(tags=["query"])


@router.post("/query", response_model=RAGResponse)
async def query_rag(body: QueryRequest) -> RAGResponse:
    """Run a retrieval query: semantic search + graph enrichment.

    Returns structured results (documents, graph nodes, relationships)
    without any LLM generation.
    """
    pipeline = GraphRAGPipeline()
    try:
        result = await pipeline.query(
            user_query=body.query,
            thread_id=body.thread_id,
            options=QueryOptions(top_k=body.top_k, max_hops=body.max_hops),
        )
    except Exception as exc:
        logger.error(
            "query_error",
            error=str(exc),
            exc_type=type(exc).__name__,
            traceback=traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}")
    return result
