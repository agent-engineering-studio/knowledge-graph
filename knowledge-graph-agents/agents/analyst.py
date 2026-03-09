"""Analyst Agent — retrieves context via KG API and calls Ollama directly for grounded answers."""

from __future__ import annotations

import os

import httpx

from tools.kg_tools import kg_retrieve_context_tool
from orchestration.state import AgentState

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_LLM_MODEL: str = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:7b")

_NO_DOCS_REPLY = {
    "it": "I documenti forniti non contengono informazioni su questo argomento.",
    "en": "The provided documents do not contain information about this topic.",
}

_ITALIAN_WORDS = ("cosa", "che", "come", "quale", "quanto", "chi", "dove", "quando", "dammi", "dimmi")


def _no_docs_message(query: str) -> str:
    q = query.lower()
    if any(w in q for w in _ITALIAN_WORDS):
        return _NO_DOCS_REPLY["it"]
    return _NO_DOCS_REPLY["en"]


_SYSTEM = (
    "You are a precise data extractor. "
    "Read the reference data provided by the user and answer questions using ONLY the values "
    "found there. Never use general knowledge or external information."
)

_TASK_TEMPLATE = """\
{reference_data}

---
TASK: Answer the question below using ONLY what is written in the <documents> above.

Rules:
1. Copy every relevant value verbatim from the documents (format: "[filename]: value").
2. After listing them, give a direct answer.
3. If no relevant value is in <documents>, reply exactly:
   "I documenti forniti non contengono informazioni su questo argomento."

Question: {question}

Values found in <documents>:"""


async def _generate(context_message: str, user_query: str) -> str:
    """Call Ollama with the raw reference data and return the grounded answer.

    context_message contains ONLY raw data (documents + graph nodes/edges).
    All instructions live here in the agent, not in the API layer.
    temperature=0 prevents the model from drifting into training-data answers.
    """
    user_message = _TASK_TEMPLATE.format(
        reference_data=context_message,
        question=user_query,
    )
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_LLM_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
                "options": {"temperature": 0, "num_predict": 1024},
            },
        )
        if response.status_code == 404:
            body = response.json() if response.content else {}
            err = body.get("error", "")
            if "not found" in err.lower():
                raise RuntimeError(
                    f"Ollama model '{OLLAMA_LLM_MODEL}' not found. "
                    f"Run: ollama pull {OLLAMA_LLM_MODEL}"
                )
        response.raise_for_status()
        return response.json()["message"]["content"]


async def analyst_node(state: AgentState) -> AgentState:
    """LangGraph node: retrieve knowledge-graph context, then call Ollama directly.

    Flow:
      1. Call kg_retrieve_context_tool (vector + keyword + graph, no LLM)
      2. If no documents found → return localised "no info" message
      3. Call Ollama with the assembled context_message as system prompt
      4. Append source references to the answer for verification
    """
    context: dict = dict(state.get("context", {}))
    thread_id: str = state.get("thread_id", "default")
    query: str = context.get("query", state.get("user_request", ""))
    top_k: int = context.get("top_k", 10)

    try:
        retrieval = await kg_retrieve_context_tool(
            query=query,
            thread_id=thread_id,
            top_k=top_k,
            max_hops=2,
        )
    except Exception as exc:
        return {
            **state,
            "context": context,
            "error": f"Analyst Agent: retrieval failed — {exc}",
            "final_output": f"Errore durante il recupero del contesto: {exc}",
        }

    context["analyst_retrieval"] = retrieval
    sources = retrieval.get("sources", [])

    # Short-circuit: no documents → skip LLM
    if not retrieval.get("has_documents", False):
        return {
            **state,
            "context": context,
            "final_output": _no_docs_message(query),
            "error": None,
        }

    # Call Ollama with the retrieval context assembled by the API
    try:
        answer = await _generate(retrieval["context_message"], query)
    except Exception as exc:
        return {
            **state,
            "context": context,
            "error": f"Analyst Agent: LLM generation failed — {exc}",
            "final_output": f"Errore durante la generazione della risposta: {exc}",
        }

    # Append source references so the user can verify retrieval
    if sources:
        source_lines = []
        for s in sources[:5]:
            name = s.get("document_name") or s.get("doc_id", "")
            preview = s.get("text_preview", "")[:120].replace("\n", " ")
            source_lines.append(f"- **{name}**: _{preview}…_")
        answer = answer + "\n\n**Fonti recuperate:**\n" + "\n".join(source_lines)

    return {
        **state,
        "context": context,
        "final_output": answer,
        "error": None,
    }
