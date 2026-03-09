"""Entity and relation extraction via Ollama LLM."""

from __future__ import annotations

import json

import httpx
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from models.graph_node import VALID_NODE_TYPES
from models.relation import VALID_RELATION_TYPES
from utils.logger import logger

# ── Result models ────────────────────────────────────────────────────

class ExtractedEntity(BaseModel):
    """An entity extracted from text."""

    id: str
    name: str
    type: str
    description: str
    importance: float
    confidence: float


class ExtractedRelation(BaseModel):
    """A relation extracted from text."""

    source_id: str
    target_id: str
    type: str
    weight: float
    confidence: float


class ExtractionResult(BaseModel):
    """Combined extraction output."""

    entities: list[ExtractedEntity]
    relations: list[ExtractedRelation]


# ── System prompt ────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""\
You are an expert knowledge-graph extraction engine.

Given a text chunk, extract **entities** and **relations** and return them as
a single valid JSON object matching this schema:

{{
  "entities": [
    {{
      "id": "<unique_slug>",
      "name": "<entity name>",
      "type": "<one of VALID_NODE_TYPES>",
      "description": "<one sentence>",
      "importance": <0.0-1.0>,
      "confidence": <0.0-1.0>
    }}
  ],
  "relations": [
    {{
      "source_id": "<entity id>",
      "target_id": "<entity id>",
      "type": "<one of VALID_RELATION_TYPES>",
      "weight": <0.0-1.0>,
      "confidence": <0.0-1.0>
    }}
  ]
}}

### Valid entity types
{", ".join(VALID_NODE_TYPES)}

### Valid relation types
{", ".join(VALID_RELATION_TYPES)}

### Rules
- Only output entities with confidence >= 0.6
- Only output relations with confidence >= 0.6
- Each entity id must be a unique lowercase slug (e.g. "acme_corp")
- Relation source_id and target_id must reference entity ids in the same result
- Return ONLY the JSON object, nothing else.

### Example 1
Text: "Google was founded by Larry Page and Sergey Brin in 1998."
Output:
{{
  "entities": [
    {{"id": "google", "name": "Google", "type": "Organization", "description": "Technology company founded in 1998.", "importance": 0.9, "confidence": 0.95}},
    {{"id": "larry_page", "name": "Larry Page", "type": "Person", "description": "Co-founder of Google.", "importance": 0.8, "confidence": 0.95}},
    {{"id": "sergey_brin", "name": "Sergey Brin", "type": "Person", "description": "Co-founder of Google.", "importance": 0.8, "confidence": 0.95}}
  ],
  "relations": [
    {{"source_id": "google", "target_id": "larry_page", "type": "CREATED_BY", "weight": 0.9, "confidence": 0.95}},
    {{"source_id": "google", "target_id": "sergey_brin", "type": "CREATED_BY", "weight": 0.9, "confidence": 0.95}}
  ]
}}

### Example 2
Text: "Redis is an in-memory data store used by many microservices at Netflix."
Output:
{{
  "entities": [
    {{"id": "redis", "name": "Redis", "type": "Technology", "description": "In-memory data store.", "importance": 0.8, "confidence": 0.9}},
    {{"id": "netflix", "name": "Netflix", "type": "Organization", "description": "Streaming platform using Redis.", "importance": 0.7, "confidence": 0.9}}
  ],
  "relations": [
    {{"source_id": "netflix", "target_id": "redis", "type": "USES", "weight": 0.8, "confidence": 0.85}}
  ]
}}
"""


# ── Extractor class ──────────────────────────────────────────────────

class EntityExtractor:
    """Extracts entities and relations from text chunks using Ollama."""

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL
        # Use dedicated extraction model if configured, otherwise fall back to LLM model.
        self.model = settings.OLLAMA_EXTRACTION_MODEL or settings.OLLAMA_LLM_MODEL

    async def extract(self, chunk: str, context: str = "") -> ExtractionResult:
        """Extract entities and relations from a text chunk.

        Args:
            chunk: The text to analyse.
            context: Optional surrounding context.

        Returns:
            An ``ExtractionResult`` with entities and relations.
        """
        user_content = chunk if not context else f"Context: {context}\n\nText: {chunk}"
        raw = await self._call_llm(user_content)

        try:
            data = json.loads(raw)
            result = ExtractionResult.model_validate(data)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("extraction_parse_error", error=str(exc), raw=raw[:200])
            return ExtractionResult(entities=[], relations=[])

        # Filter by confidence threshold
        result.entities = [e for e in result.entities if e.confidence >= 0.6]
        result.relations = [r for r in result.relations if r.confidence >= 0.6]

        logger.info(
            "extraction_complete",
            entities=len(result.entities),
            relations=len(result.relations),
        )
        return result

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def _call_llm(self, user_content: str) -> str:
        """Call the Ollama chat endpoint and return the raw message content."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "stream": False,
                    "format": "json",
                },
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
