"""Analyst Agent — retrieves KG context and answers questions grounded in documents.

Uses the Microsoft Agent Framework ``client.as_agent()`` + ``AgentSession`` pattern.

Context retrieval is done explicitly in Python (not via LLM tool-calling) because
local models like qwen2.5:7b may not call tools reliably via the OpenAI-compatible
API.  The retrieved context is injected directly into the user message so the LLM
only needs to generate a grounded answer — no tool invocation required.

The ``RedisHistoryProvider`` injects past conversation turns into the agent's
system instructions before each run.
"""

from __future__ import annotations

from agent_framework import AgentSession

from agents.client import get_client
from memory.redis_history import RedisHistoryProvider
from tools.kg_tools import kg_retrieve_context_tool

_NO_DOCS_IT = "I documenti forniti non contengono informazioni su questo argomento."
_NO_DOCS_EN = "The provided documents do not contain information about this topic."
_ITALIAN_WORDS = ("cosa", "che", "come", "quale", "quanto", "chi", "dove", "quando", "dammi", "dimmi")


def _no_docs_message(query: str) -> str:
    return _NO_DOCS_IT if any(w in query.lower() for w in _ITALIAN_WORDS) else _NO_DOCS_EN


_ANALYST_INSTRUCTIONS = """\
You are a precise data extractor for a Knowledge Graph system.

## Your task
The user message contains reference data retrieved from the Knowledge Graph,
followed by a question.  Answer the question using ONLY the values found in
the reference data.  Never rely on your general training knowledge.

## Rules
1. Copy every relevant value verbatim from the reference data (format: "[source]: value").
2. After listing them, give a concise direct answer.
3. If the question is a follow-up, use the conversation history in your system
   instructions to understand the context.
4. If no relevant value is found in the reference data, reply exactly:
   "I documenti forniti non contengono informazioni su questo argomento."

## Constraints
- Be deterministic and precise.
- Do not speculate or add information not present in the reference data.
"""

_history_provider = RedisHistoryProvider()

_CONTEXT_TEMPLATE = """\
<reference_data>
{context_message}
</reference_data>

---
QUESTION: {question}

Values found in <reference_data>:"""


def create_analyst_agent(thread_id: str):
    """Create an analyst agent for the given namespace/thread.

    No tools are registered — context is pre-fetched in Python and injected
    into the prompt, making the agent reliable even with local LLMs that do
    not support tool-calling.
    """
    client = get_client()
    return client.as_agent(
        name="analyst",
        instructions=_ANALYST_INSTRUCTIONS,
        context_providers=[_history_provider],
    )


async def run_analyst(request: str, thread_id: str) -> str:
    """Run the analyst agent and return a grounded answer.

    Flow:
      1. Retrieve KG context explicitly in Python (vector + graph, no LLM).
      2. If no documents → return localised "no info" message immediately.
      3. Build an augmented prompt that embeds the context alongside the question.
      4. Run the MAF agent — the LLM generates an answer from the prompt context.
      5. Append source references for verification.
    """
    # Step 1: explicit retrieval (no LLM tool-calling)
    try:
        retrieval = await kg_retrieve_context_tool(
            query=request, thread_id=thread_id, top_k=10, max_hops=2
        )
    except Exception as exc:
        return f"Errore durante il recupero del contesto: {exc}"

    # Step 2: short-circuit if no documents
    if not retrieval.get("has_documents", False):
        return _no_docs_message(request)

    context_message: str = retrieval.get("context_message", "")
    sources: list = retrieval.get("sources", [])

    # Step 3: build prompt with embedded context
    augmented_prompt = _CONTEXT_TEMPLATE.format(
        context_message=context_message,
        question=request,
    )

    # Step 4: MAF agent generates the grounded answer
    agent = create_analyst_agent(thread_id)
    session: AgentSession = agent.create_session()
    session.state["thread_id"] = thread_id

    try:
        answer = str(await agent.run(augmented_prompt, session=session))
    except Exception as exc:
        return f"Errore durante la generazione della risposta: {exc}"

    # Step 5: append source references
    if sources:
        lines = []
        for s in sources[:5]:
            name = s.get("document_name") or s.get("doc_id", "")
            preview = s.get("text_preview", "")[:120].replace("\n", " ")
            lines.append(f"- **{name}**: _{preview}…_")
        answer = answer + "\n\n**Fonti recuperate:**\n" + "\n".join(lines)

    return answer
