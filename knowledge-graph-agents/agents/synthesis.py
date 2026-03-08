"""Synthesis Agent — generates structured reports from KG data via Ollama."""

from __future__ import annotations

import os

import httpx

from tools.kg_tools import kg_ingest_tool, kg_query_tool
from orchestration.state import AgentState

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_LLM_MODEL: str = os.getenv("OLLAMA_LLM_MODEL", "llama3")

_SYNTHESIS_SYSTEM_PROMPT = """\
Sei un assistente specializzato nella sintesi di informazioni provenienti da un Knowledge Graph.
Genera un report strutturato in Markdown basandoti ESCLUSIVAMENTE sul contesto fornito.
Se il contesto è insufficiente, indicalo chiaramente.

## Contesto KG
{context}

## Formato richiesto
{output_format}
"""


async def _call_ollama(system: str, user_prompt: str) -> str:
    """Call Ollama for text generation."""
    async with httpx.AsyncClient(
        base_url=OLLAMA_BASE_URL, timeout=120.0
    ) as client:
        r = await client.post(
            "/api/chat",
            json={
                "model": OLLAMA_LLM_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
            },
        )
        r.raise_for_status()
        return r.json()["message"]["content"]


async def generate_report(
    topic: str,
    namespace: str,
    output_format: str = "executive summary in Markdown",
    kgc_proposals: dict | None = None,
    analyst_result: dict | None = None,
) -> str:
    """Retrieve context from the KG and generate a formatted report.

    Args:
        topic: The report subject.
        namespace: The KG namespace to query.
        output_format: Instructions for the output format.
        kgc_proposals: Optional KGC proposals to include in the context.
        analyst_result: Optional analyst search result to include.

    Returns:
        Generated Markdown report as a string.
    """
    rag_result = await kg_query_tool(
        query=topic, thread_id=namespace, top_k=15, max_hops=2
    )

    context_parts: list[str] = []

    rag_answer = rag_result.get("answer", "")
    if rag_answer:
        context_parts.append(f"### Risposta RAG\n{rag_answer}")

    if analyst_result:
        analyst_answer = analyst_result.get("answer", "")
        if analyst_answer:
            context_parts.append(f"### Analisi grafo\n{analyst_answer}")

    if kgc_proposals:
        rels = kgc_proposals.get("new_relations", [])
        if rels:
            rel_lines = [
                f"- {r['source_name']} → {r['proposed_relation']} → {r['target_name']} "
                f"(confidence: {r['confidence']:.0%})"
                for r in rels[:10]
            ]
            context_parts.append("### Relazioni mancanti identificate\n" + "\n".join(rel_lines))

    if not context_parts:
        return f"Nessun contesto trovato nel KG per il topic: {topic}"

    full_context = "\n\n".join(context_parts)
    system_prompt = _SYNTHESIS_SYSTEM_PROMPT.format(
        context=full_context,
        output_format=output_format,
    )

    return await _call_ollama(system_prompt, f"Genera un report su: {topic}")


async def synthesis_node(state: AgentState) -> AgentState:
    """LangGraph node: generate a structured report and store it in context."""
    context: dict = dict(state.get("context", {}))
    thread_id: str = state.get("thread_id", "default")
    topic: str = context.get("topic", state.get("user_request", ""))
    output_format: str = context.get("output_format", "executive summary in Markdown")
    auto_ingest: bool = context.get("auto_ingest_report", False)

    try:
        report = await generate_report(
            topic=topic,
            namespace=thread_id,
            output_format=output_format,
            kgc_proposals=context.get("kgc_proposal"),
            analyst_result=context.get("analyst_result"),
        )
    except Exception as exc:
        return {
            **state,
            "context": context,
            "error": f"Synthesis Agent: report generation failed — {exc}",
            "final_output": f"Errore nella generazione del report: {exc}",
        }

    context["synthesis_report"] = report

    # Optional: auto-ingest the generated report back into the KG
    if auto_ingest:
        try:
            import tempfile, os
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(report)
                tmp_path = tmp.name
            await kg_ingest_tool(
                file_path=tmp_path,
                thread_id=thread_id,
                skip_existing=True,
            )
            os.unlink(tmp_path)
        except Exception:
            pass  # auto-ingest is best-effort

    return {
        **state,
        "context": context,
        "final_output": report,
        "error": None,
    }
