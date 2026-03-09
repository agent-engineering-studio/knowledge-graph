"""Ingestion routes."""

from __future__ import annotations

import os
import pathlib
import tempfile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.schemas import IngestRequest
from pipeline.ingest import IngestOptions, IngestResult, IngestionPipeline
from utils.logger import logger

router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=IngestResult)
async def ingest_document(body: IngestRequest) -> IngestResult:
    """Ingest a document through the full pipeline via server-side file path.

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


@router.post("/ingest/upload", response_model=IngestResult)
async def upload_and_ingest(
    file: UploadFile = File(...),
    thread_id: str = Form("default"),
    skip_existing: bool = Form(True),
) -> IngestResult:
    """Upload a document and ingest it through the full pipeline.

    Accepts multipart/form-data so the client can send a file directly
    without needing server-side filesystem access.

    Args:
        file: The uploaded document (PDF, DOCX, or TXT).
        thread_id: Namespace / partition key.
        skip_existing: Skip chunks already present via SHA-256 dedup.

    Returns:
        An ``IngestResult`` summary.
    """
    original_name = pathlib.Path(file.filename or "upload")
    suffix = original_name.suffix or ".bin"
    # Keep the original stem in the temp filename so the document name is readable
    safe_stem = "".join(c if c.isalnum() or c in "-_ " else "_" for c in original_name.stem)[:60]

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            prefix=safe_stem + "_",
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        logger.info("upload_received", filename=file.filename, size=len(content), tmp=tmp_path)

        pipeline = IngestionPipeline()
        try:
            result = await pipeline.ingest(
                file_path=tmp_path,
                thread_id=thread_id,
                options=IngestOptions(skip_existing=skip_existing),
            )
        except ValueError as exc:
            logger.error("ingest_error", error=str(exc))
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            logger.error("ingest_error", error=str(exc))
            raise HTTPException(status_code=500, detail="Ingestion failed")

    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return result
