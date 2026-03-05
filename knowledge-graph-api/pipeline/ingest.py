"""Ingestion pipeline — 8 stage document processing."""

from __future__ import annotations

import hashlib
import time

from pydantic import BaseModel

from config.settings import settings
from models.base import VectorDocument
from models.graph_node import GraphNode
from models.relation import Relation
from pipeline.chunker import TextChunker
from pipeline.content_extractor import ContentExtractor
from pipeline.embedder import Embedder
from pipeline.extractor import EntityExtractor
from pipeline.router import resolve_mime_type
from storage.neo4j_graph import Neo4jGraph
from storage.redis_vector import RedisVectorStore
from utils.logger import logger


class IngestOptions(BaseModel):
    """Options for the ingestion pipeline."""

    skip_existing: bool = True


class IngestResult(BaseModel):
    """Result summary of a document ingestion run."""

    document_id: str
    chunks_processed: int
    chunks_skipped: int
    entities_extracted: int
    relations_extracted: int
    nodes_created: int
    edges_created: int
    processing_time_ms: float
    errors: list[str]


class IngestionPipeline:
    """Orchestrates the 8-stage ingestion flow."""

    def __init__(self) -> None:
        self.content_extractor = ContentExtractor()
        self.chunker = TextChunker()
        self.embedder = Embedder()
        self.entity_extractor = EntityExtractor()
        self.vector_store = RedisVectorStore()
        self.graph = Neo4jGraph()

    async def ingest(
        self,
        file_path: str,
        thread_id: str,
        options: IngestOptions | None = None,
    ) -> IngestResult:
        """Run the full ingestion pipeline on a file.

        Args:
            file_path: Path to the source document.
            thread_id: Namespace / partition key.
            options: Optional processing options.

        Returns:
            An ``IngestResult`` summary.
        """
        options = options or IngestOptions()
        start = time.perf_counter()
        errors: list[str] = []

        # 1 — Routing
        mime_type = resolve_mime_type(file_path)
        logger.info("ingest_start", file=file_path, mime=mime_type)

        # 2 — Content extraction
        text, total_pages = await self.content_extractor.extract(file_path)

        # 3 — Chunking
        chunks = self.chunker.split(text)
        logger.info("chunks_created", count=len(chunks))

        # 4 — Embedding
        vectors = await self.embedder.embed(chunks)

        chunks_processed = 0
        chunks_skipped = 0
        total_entities = 0
        total_relations = 0
        nodes_created = 0
        edges_created = 0
        document_id = ""

        for idx, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            # 5 — Smart re-ingestion (SHA-256 dedup)
            content_hash = hashlib.sha256(chunk_text.encode()).hexdigest()
            if options.skip_existing:
                existing = await self.vector_store.get_by_hash(content_hash)
                if existing is not None:
                    chunks_skipped += 1
                    continue

            # 6 — Entity extraction
            try:
                extraction = await self.entity_extractor.extract(chunk_text)
            except Exception as exc:
                logger.error("entity_extraction_failed", chunk=idx, error=str(exc))
                errors.append(f"chunk {idx}: entity extraction failed — {exc}")
                extraction = None

            # 7 — Vector store
            doc = VectorDocument(
                thread_id=thread_id,
                text=chunk_text,
                name=file_path,
                vector=vector,
                page_number=idx,
                total_pages=total_pages,
                content_hash=content_hash,
                mime_type=mime_type,
            )
            if not document_id:
                document_id = doc.id
                doc.base_document_id = document_id
            else:
                doc.base_document_id = document_id

            await self.vector_store.upsert(doc)
            chunks_processed += 1

            # 8 — Graph ingestion
            if extraction:
                for entity in extraction.entities:
                    node = GraphNode(
                        id=entity.id,
                        name=entity.name,
                        label=entity.type,
                        node_type=entity.type,
                        namespace=thread_id,
                        importance=entity.importance,
                        confidence=entity.confidence,
                        description=entity.description,
                        source_chunk_ids=[doc.id],
                    )
                    await self.graph.upsert_node(node)
                    nodes_created += 1

                for rel in extraction.relations:
                    relation = Relation(
                        source_id=rel.source_id,
                        target_id=rel.target_id,
                        label=rel.type,
                        relation_type=rel.type,
                        weight=rel.weight,
                        confidence=rel.confidence,
                        namespace=thread_id,
                    )
                    await self.graph.upsert_relation(relation)
                    edges_created += 1

                total_entities += len(extraction.entities)
                total_relations += len(extraction.relations)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "ingest_complete",
            document_id=document_id,
            chunks=chunks_processed,
            skipped=chunks_skipped,
            entities=total_entities,
            relations=total_relations,
            ms=round(elapsed_ms, 1),
        )

        return IngestResult(
            document_id=document_id,
            chunks_processed=chunks_processed,
            chunks_skipped=chunks_skipped,
            entities_extracted=total_entities,
            relations_extracted=total_relations,
            nodes_created=nodes_created,
            edges_created=edges_created,
            processing_time_ms=round(elapsed_ms, 1),
            errors=errors,
        )
