"""Document listing routes."""

from __future__ import annotations

from fastapi import APIRouter

from storage.redis_vector import RedisVectorStore

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{namespace}")
async def list_documents(namespace: str) -> dict:
    """List all documents in a namespace.

    Args:
        namespace: The thread_id / namespace.

    Returns:
        List of document summaries (without vectors).
    """
    store = RedisVectorStore()
    try:
        docs = await store.list_by_namespace(namespace)
        # Group chunks by base_document_id → one entry per unique document
        groups: dict[str, dict] = {}
        for d in docs:
            key = d.base_document_id or d.id
            if key not in groups:
                groups[key] = {
                    "base_document_id": key,
                    "name": d.name,
                    "mime_type": d.mime_type,
                    "total_pages": d.total_pages,
                    "created_at": d.created_at.isoformat(),
                    "chunk_count": 0,
                }
            groups[key]["chunk_count"] += 1
        return {"documents": list(groups.values())}
    finally:
        await store.close()
