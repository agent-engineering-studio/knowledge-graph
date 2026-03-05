"""Query and streaming routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.schemas import QueryRequest
from query.rag_pipeline import GraphRAGPipeline, QueryOptions, RAGResponse
from utils.logger import logger

router = APIRouter(tags=["query"])


@router.post("/query", response_model=RAGResponse)
async def query_rag(body: QueryRequest) -> RAGResponse:
    """Run a RAG query and return a structured response.

    Args:
        body: The query request payload.

    Returns:
        A ``RAGResponse``.
    """
    pipeline = GraphRAGPipeline()
    try:
        result = await pipeline.query(
            user_query=body.query,
            thread_id=body.thread_id,
            options=QueryOptions(top_k=body.top_k, max_hops=body.max_hops, stream=False),
        )
    except Exception as exc:
        logger.error("query_error", error=str(exc))
        raise HTTPException(status_code=500, detail="Query failed")
    return result


@router.post("/query/stream")
async def query_rag_stream(body: QueryRequest) -> StreamingResponse:
    """Run a RAG query with Server-Sent Events streaming.

    Args:
        body: The query request payload.

    Returns:
        A ``StreamingResponse`` with SSE content.
    """
    pipeline = GraphRAGPipeline()

    async def _event_generator():
        try:
            gen = await pipeline.query(
                user_query=body.query,
                thread_id=body.thread_id,
                options=QueryOptions(top_k=body.top_k, max_hops=body.max_hops, stream=True),
            )
            async for chunk in gen:
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error("stream_error", error=str(exc))
            yield f"data: [ERROR] {exc}\n\n"

    return StreamingResponse(_event_generator(), media_type="text/event-stream")
