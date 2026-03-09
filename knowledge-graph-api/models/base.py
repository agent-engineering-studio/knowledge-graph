"""Base models for the vector store."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field


class VectorDocument(BaseModel):
    """Document stored in the Redis vector store."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    thread_id: str
    text: str
    name: str
    vector: list[float] = Field(default_factory=list)
    description: str | None = None
    page_number: int = 0
    total_pages: int = 0
    content_hash: str | None = None
    base_document_id: str | None = None
    mime_type: str | None = None
    node_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
