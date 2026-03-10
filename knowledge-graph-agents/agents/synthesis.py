"""Synthesis Agent — generates structured Markdown reports from KG data.

Uses the Microsoft Agent Framework ``client.as_agent()`` + ``AgentSession`` pattern.

KG context is pre-fetched in Python (same pattern as the analyst agent) so the
LLM does not need to call tools — it only generates the structured report from
the embedded context.  This works reliably with local models that lack reliable
tool-calling support.
"""

from __future__ import annotations

from agent_framework import AgentSession

from agents.client import get_client
from tools.kg_tools import kg_query_tool

_SYNTHESIS_INSTRUCTIONS = """\
Sei un assistente specializzato nella sintesi di informazioni provenienti da un Knowledge Graph.

## Il tuo compito
Il messaggio utente contiene dati recuperati dal Knowledge Graph.
Genera un report strutturato in Markdown basandoti ESCLUSIVAMENTE su quei dati.
Non inventare informazioni.

## Formato del report
- **Titolo** (H1): argomento principale
- **Executive Summary** (H2): 3-5 punti chiave
- **Dettagli** (H2): analisi approfondita
- **Fonti** (H2): elenco delle fonti citate nei dati
- **Conclusioni** (H2): sintesi finale

Se il contesto è insufficiente, indicalo chiaramente.
"""


def create_synthesis_agent(thread_id: str):
    """Create a synthesis agent (no tools — context injected in prompt)."""
    client = get_client()
    return client.as_agent(
        name="synthesis",
        instructions=_SYNTHESIS_INSTRUCTIONS,
    )


async def run_synthesis(request: str, thread_id: str) -> str:
    """Pre-fetch KG context, then run the synthesis agent to generate a report."""
    # Pre-fetch context via RAG query (explicit, not via LLM tool-calling)
    context_parts: list[str] = []
    try:
        rag = await kg_query_tool(query=request, thread_id=thread_id, top_k=15, max_hops=2)
        if rag.get("answer"):
            context_parts.append(f"### Risposta RAG\n{rag['answer']}")
        if rag.get("sources"):
            src_lines = [
                f"- {s.get('document_name') or s.get('doc_id', '')}: {s.get('text_preview', '')[:100]}"
                for s in rag["sources"][:5]
            ]
            context_parts.append("### Fonti\n" + "\n".join(src_lines))
    except Exception:
        pass

    if not context_parts:
        return f"Nessun contesto trovato nel KG per: {request}"

    augmented_prompt = (
        f"<kg_context>\n{chr(10).join(context_parts)}\n</kg_context>\n\n"
        f"Genera un report su: {request}"
    )

    agent = create_synthesis_agent(thread_id)
    session: AgentSession = agent.create_session()
    session.state["thread_id"] = thread_id

    try:
        return str(await agent.run(augmented_prompt, session=session))
    except Exception as exc:
        return f"Errore nella generazione del report: {exc}"
