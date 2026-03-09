"""Query and streaming routes."""

from __future__ import annotations

import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.schemas import QueryRequest
from query.rag_pipeline import GraphRAGPipeline, QueryOptions, RAGResponse
from utils.logger import logger

router = APIRouter(tags=["query"])


@router.post("/query", response_model=RAGResponse)
async def query_rag(body: QueryRequest) -> RAGResponse:
    """Run a RAG query and return a structured response."""
    pipeline = GraphRAGPipeline()
    try:
        result = await pipeline.query(
            user_query=body.query,
            thread_id=body.thread_id,
            options=QueryOptions(top_k=body.top_k, max_hops=body.max_hops, stream=False),
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


@router.post("/query/stream")
async def query_rag_stream(body: QueryRequest) -> StreamingResponse:
    """Run a RAG query with Server-Sent Events streaming."""
    pipeline = GraphRAGPipeline()

    async def _event_generator():
        try:
            logger.info("stream_start", query=body.query[:80], thread_id=body.thread_id)
            gen = await pipeline.query(
                user_query=body.query,
                thread_id=body.thread_id,
                options=QueryOptions(top_k=body.top_k, max_hops=body.max_hops, stream=True),
            )
            logger.info("stream_llm_start")
            chunk_count = 0
            async for chunk in gen:
                chunk_count += 1
                yield f"data: {chunk}\n\n"
            logger.info("stream_complete", chunks=chunk_count)
            yield "data: [DONE]\n\n"
        except Exception as exc:
            tb = traceback.format_exc()
            logger.error(
                "stream_error",
                error=str(exc) or repr(exc),
                exc_type=type(exc).__name__,
                traceback=tb,
            )
            yield f"data: [ERROR] {type(exc).__name__}: {exc}\n\n"

    return StreamingResponse(_event_generator(), media_type="text/event-stream")
