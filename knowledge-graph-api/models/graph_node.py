"""Graph node model for Neo4j."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

VALID_NODE_TYPES = [
    "Person", "Organization", "Product", "Technology",
    "Process", "Event", "Location", "Concept",
    "Document", "Category", "Tag",
]


class GraphNode(BaseModel):
    """Node entity stored in the Neo4j graph database."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    slug: str = ""  # LLM-generated entity key used as dedup identifier (e.g. "globuli_rossi")
    name: str
    label: str
    node_type: str
    namespace: str
    importance: float = 0.5
    confidence: float = 0.8
    description: str | None = None
    source_chunk_ids: list[str] = Field(default_factory=list)
    embedding: list[float] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)
