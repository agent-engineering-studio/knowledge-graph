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
        return {
            "documents": [
                {
                    "id": d.id,
                    "name": d.name,
                    "thread_id": d.thread_id,
                    "content_hash": d.content_hash,
                    "mime_type": d.mime_type,
                    "page_number": d.page_number,
                    "created_at": d.created_at.isoformat(),
                }
                for d in docs
            ]
        }
    finally:
        await store.close()
