"""Ingestion Agent — manages the full document lifecycle in the Knowledge Graph.

Uses the Microsoft Agent Framework ``client.as_agent()`` pattern.
The agent's LLM orchestrates: health-check → list existing docs → ingest.
"""

from __future__ import annotations

from agent_framework import AgentSession

from agents.client import get_client
from tools.kg_tools import make_ingest_tools

_INGESTION_INSTRUCTIONS = """\
You are a document ingestion agent for a Knowledge Graph system.

## Your task
Ingest a document file into the Knowledge Graph pipeline following these steps:

1. Call `check_kg_health` to verify all services (Neo4j, Redis, Ollama) are running.
   If any service is unavailable, stop and report the issue.

2. Call `list_kg_documents` to check for existing documents (dedup pre-check).

3. Call `ingest_document` with the file path provided in the user request.
   Use `skip_existing=true` to avoid reprocessing duplicate chunks.

4. Report the ingestion result with:
   - Chunks processed / skipped
   - Entities and relations extracted
   - Nodes and edges created in Neo4j
   - Processing time

## Error handling
If ingestion fails, explain the error clearly and suggest corrective action.
"""


def create_ingestion_agent(thread_id: str):
    """Create an ingestion agent for the given namespace/thread."""
    client = get_client()
    tools = make_ingest_tools(thread_id)
    return client.as_agent(
        name="ingestion",
        instructions=_INGESTION_INSTRUCTIONS,
        tools=tools,
    )


async def run_ingestion(request: str, thread_id: str) -> str:
    """Run the ingestion agent and return the result summary."""
    agent = create_ingestion_agent(thread_id)
    session: AgentSession = agent.create_session()
    session.state["thread_id"] = thread_id
    return str(await agent.run(request, session=session))
