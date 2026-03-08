"""Ingestion Agent — manages the full document lifecycle in the KG."""

from __future__ import annotations

from tools.kg_tools import kg_health_tool, kg_ingest_tool, kg_list_documents_tool
from orchestration.state import AgentState


async def ingestion_node(state: AgentState) -> AgentState:
    """LangGraph node: ingest a document and update the shared state.

    Reads ``context["file_path"]`` (required) and uses the ``thread_id`` from
    the shared state.  On success writes the ``IngestResult`` dict into
    ``context["ingestion_result"]``.
    """
    context: dict = dict(state.get("context", {}))
    thread_id: str = state.get("thread_id", "default")
    file_path: str = context.get("file_path", "")

    if not file_path:
        return {
            **state,
            "error": "Ingestion Agent: context['file_path'] is required",
            "final_output": "Errore: nessun file specificato per l'ingestion.",
        }

    # Pre-check: verify the API is healthy
    try:
        health = await kg_health_tool()
        if health.get("status") != "ok":
            return {
                **state,
                "error": "Ingestion Agent: KG API health check failed",
                "final_output": "Errore: il servizio KG non è disponibile.",
            }
    except Exception as exc:
        return {
            **state,
            "error": f"Ingestion Agent: health check error — {exc}",
            "final_output": "Errore: impossibile raggiungere il servizio KG.",
        }

    # Optional dedup pre-check
    try:
        existing_docs = await kg_list_documents_tool(thread_id)
        existing_names = [d.get("name", "") for d in existing_docs.get("documents", [])]
        context["existing_doc_count"] = len(existing_names)
    except Exception:
        context["existing_doc_count"] = 0

    # Main ingestion
    try:
        result = await kg_ingest_tool(
            file_path=file_path,
            thread_id=thread_id,
            skip_existing=context.get("skip_existing", True),
        )
    except Exception as exc:
        return {
            **state,
            "context": context,
            "error": f"Ingestion Agent: ingest failed — {exc}",
            "final_output": f"Errore durante l'ingestion di '{file_path}': {exc}",
        }

    context["ingestion_result"] = result

    summary = (
        f"Documento '{file_path}' ingestito con successo.\n"
        f"- Chunks processati: {result.get('chunks_processed', 0)}\n"
        f"- Chunks saltati (dedup): {result.get('chunks_skipped', 0)}\n"
        f"- Entità estratte: {result.get('entities_extracted', 0)}\n"
        f"- Relazioni estratte: {result.get('relations_extracted', 0)}\n"
        f"- Nodi creati: {result.get('nodes_created', 0)}\n"
        f"- Archi creati: {result.get('edges_created', 0)}\n"
        f"- Tempo: {result.get('processing_time_ms', 0):.0f} ms"
    )
    if result.get("errors"):
        summary += f"\n- Errori: {result['errors']}"

    return {
        **state,
        "context": context,
        "final_output": summary,
        "error": None,
    }
