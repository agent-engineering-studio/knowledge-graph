"""Request and response schemas for the API."""

from __future__ import annotations

from pydantic import BaseModel


class IngestRequest(BaseModel):
    """Body for POST /ingest."""

    file_path: str
    thread_id: str
    skip_existing: bool = True


class QueryRequest(BaseModel):
    """Body for POST /query and POST /query/stream."""

    query: str
    thread_id: str
    top_k: int = 10
    max_hops: int = 2


class HealthResponse(BaseModel):
    """Response for GET /health."""

    status: str
    neo4j: bool
    redis: bool
    ollama: bool
