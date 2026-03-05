"""Ingestion routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import IngestRequest
from pipeline.ingest import IngestOptions, IngestResult, IngestionPipeline
from utils.logger import logger

router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=IngestResult)
async def ingest_document(body: IngestRequest) -> IngestResult:
    """Ingest a document through the full pipeline.

    Args:
        body: The ingestion request payload.

    Returns:
        An ``IngestResult`` summary.
    """
    pipeline = IngestionPipeline()
    try:
        result = await pipeline.ingest(
            file_path=body.file_path,
            thread_id=body.thread_id,
            options=IngestOptions(skip_existing=body.skip_existing),
        )
    except ValueError as exc:
        logger.error("ingest_error", error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("ingest_error", error=str(exc))
        raise HTTPException(status_code=500, detail="Ingestion failed")
    return result
