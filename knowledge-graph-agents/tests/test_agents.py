"""Unit tests for the multi-agent Knowledge Graph system.

All tests use ``unittest.mock`` to patch httpx calls so no live services are
required.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from orchestration.router import classify_intent
from orchestration.state import Intent
from orchestration.planner import build_plan


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_response(data: dict, status_code: int = 200):
    """Create a mock httpx.Response-like object."""
    mock = AsyncMock()
    mock.status_code = status_code
    mock.json.return_value = data
    mock.raise_for_status = AsyncMock()
    return mock


# ── Intent classification ─────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("carica questo documento", Intent.INGEST),
    ("upload the file", Intent.INGEST),
    ("cosa sai su Hevolus?", Intent.QUERY),
    ("analizza le entità presenti", Intent.ANALYZE),
    ("genera un report su AR", Intent.SYNTHESIZE),
    ("verifica qualità del grafo", Intent.VALIDATE),
    ("relazioni mancanti nel grafo", Intent.KGC),
    ("salute del sistema", Intent.MONITOR),
    ("frase senza pattern specifico", Intent.QUERY),  # fallback
])
def test_intent_classification(text: str, expected: Intent):
    result = classify_intent(text)
    assert result == expected


# ── Planner ───────────────────────────────────────────────────────────────────

def test_build_plan_ingest():
    plan = build_plan(Intent.INGEST)
    agents = [s.agent for s in plan]
    assert "ingestion" in agents
    assert "validator" in agents


def test_build_plan_synthesize():
    plan = build_plan(Intent.SYNTHESIZE)
    agents = [s.agent for s in plan]
    assert "synthesis" in agents


def test_build_plan_kgc():
    plan = build_plan(Intent.KGC)
    agents = [s.agent for s in plan]
    assert "kgc" in agents
    assert "synthesis" in agents


# ── Ingestion Agent ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingestion_agent_success():
    from agents.ingestion import ingestion_node

    ingest_response = {
        "document_id": "doc-123",
        "chunks_processed": 45,
        "chunks_skipped": 0,
        "entities_extracted": 12,
        "relations_extracted": 8,
        "nodes_created": 12,
        "edges_created": 8,
        "processing_time_ms": 1234.5,
        "errors": [],
    }
    health_response = {"status": "ok", "neo4j": True, "redis": True, "ollama": True}
    docs_response = {"documents": []}

    with (
        patch("tools.kg_tools.httpx.AsyncClient") as mock_cls,
    ):
        instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        instance.get.return_value = _mock_response(health_response)
        instance.post.return_value = _mock_response(ingest_response)

        # list_documents uses GET
        instance.get.side_effect = [
            _mock_response(health_response),
            _mock_response(docs_response),
        ]
        instance.post.return_value = _mock_response(ingest_response)

        state = {
            "user_request": "carica doc.pdf",
            "intent": "ingest",
            "plan": [],
            "current_step": 0,
            "context": {"file_path": "/data/doc.pdf"},
            "final_output": None,
            "error": None,
            "thread_id": "default",
            "run_id": "run-001",
        }

        result = await ingestion_node(state)

    assert result["error"] is None
    assert "doc.pdf" in result["final_output"]


@pytest.mark.asyncio
async def test_ingestion_agent_missing_file():
    from agents.ingestion import ingestion_node

    state = {
        "user_request": "carica",
        "intent": "ingest",
        "plan": [],
        "current_step": 0,
        "context": {},  # no file_path
        "final_output": None,
        "error": None,
        "thread_id": "default",
        "run_id": "run-002",
    }
    result = await ingestion_node(state)
    assert result["error"] is not None
    assert "file_path" in result["error"]


# ── Analyst Agent ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyst_agent_vector():
    from agents.analyst import analyst_node

    rag_response = {
        "answer": "Hevolus è una società specializzata in AR enterprise.",
        "sources": [{"doc_id": "d1", "text_preview": "...", "score": 0.9}],
        "nodes_used": ["node-1"],
        "edges_used": [],
        "query_intent": "entity_query",
        "processing_time_ms": 890.0,
    }

    with patch("tools.kg_tools.httpx.AsyncClient") as mock_cls:
        instance = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=instance)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        instance.post.return_value = _mock_response(rag_response)

        state = {
            "user_request": "cosa sai su Hevolus?",
            "intent": "query",
            "plan": [],
            "current_step": 0,
            "context": {"analyst_strategy": "vector", "query": "cosa sai su Hevolus?"},
            "final_output": None,
            "error": None,
            "thread_id": "default",
            "run_id": "run-003",
        }

        result = await analyst_node(state)

    assert result["error"] is None
    assert "Hevolus" in result["final_output"]


# ── Validator Agent ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validator_agent():
    from agents.validator import validator_node

    cypher_responses = [
        {"results": [{"orphan_count": 3}]},
        {"results": [{"node_count": 50}]},
        {"results": [{"rel_count": 120}]},
        {"results": [{"no_embed_count": 5}]},
    ]
    call_count = 0

    async def fake_cypher_tool(query, namespace, params=None):
        nonlocal call_count
        resp = cypher_responses[call_count % len(cypher_responses)]
        call_count += 1
        return resp

    with patch("agents.validator.kg_cypher_tool", side_effect=fake_cypher_tool):
        state = {
            "user_request": "verifica qualità",
            "intent": "validate",
            "plan": [],
            "current_step": 0,
            "context": {},
            "final_output": None,
            "error": None,
            "thread_id": "default",
            "run_id": "run-004",
        }

        result = await validator_node(state)

    assert result["error"] is None
    assert "quality_report" in result["context"]
    assert result["context"]["quality_report"]["total_nodes"] == 50


# ── Orchestrator ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_orchestrator_plan_ingest():
    from agents.orchestrator import orchestrator_node

    state = {
        "user_request": "carica il documento report.pdf",
        "intent": None,
        "plan": [],
        "current_step": 0,
        "context": {},
        "final_output": None,
        "error": None,
        "thread_id": "default",
        "run_id": "run-005",
    }

    result = await orchestrator_node(state)

    assert result["intent"] == Intent.INGEST.value
    agents_in_plan = [s["agent"] for s in result["plan"]]
    assert "ingestion" in agents_in_plan


@pytest.mark.asyncio
async def test_orchestrator_plan_query():
    from agents.orchestrator import orchestrator_node

    state = {
        "user_request": "cosa sai su intelligenza artificiale?",
        "intent": None,
        "plan": [],
        "current_step": 0,
        "context": {},
        "final_output": None,
        "error": None,
        "thread_id": "default",
        "run_id": "run-006",
    }

    result = await orchestrator_node(state)

    assert result["intent"] == Intent.QUERY.value
    agents_in_plan = [s["agent"] for s in result["plan"]]
    assert "analyst" in agents_in_plan
