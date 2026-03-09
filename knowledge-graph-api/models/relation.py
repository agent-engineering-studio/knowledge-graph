"""Relation model for Neo4j edges."""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

VALID_RELATION_TYPES = [
    # Core
    "BELONGS_TO", "RELATES_TO", "CREATED_BY", "MENTIONS",
    "PART_OF", "USES", "LOCATED_IN", "OCCURRED_AT",
    "HAS_TAG", "SIMILAR_TO", "DEPENDS_ON", "REPLACED_BY",
    # Authorship / contribution
    "EDITED_BY", "WRITTEN_BY", "DIRECTED_BY", "PRODUCED_BY",
    "COLLABORATED_WITH", "CONTRIBUTED_TO", "PUBLISHED_BY",
    # Discovery / science
    "DISCOVERED_BY", "OBSERVED_BY", "MEASURED_BY", "STUDIED_BY",
    "NAMED_AFTER", "COMPOSED_OF", "CONTAINS",
    # Relationships
    "WORKS_FOR", "FOUNDED_BY", "LED_BY", "PARTICIPATED_IN",
    "ASSOCIATED_WITH", "CONNECTED_TO", "INFLUENCED_BY",
]


class Relation(BaseModel):
    """Directed relation (edge) between two graph nodes."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    target_id: str
    label: str
    relation_type: str
    weight: float = 0.5
    confidence: float = 0.8
    namespace: str
    properties: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
