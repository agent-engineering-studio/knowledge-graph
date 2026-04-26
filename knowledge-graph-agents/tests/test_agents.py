"""Unit tests for the multi-agent Knowledge Graph system (Microsoft Agent Framework).

All tests use ``unittest.mock`` to patch external calls so no live services are
required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.orchestrator import classify_intent
from orchestration.state import Intent
from orchestration.planner import build_plan


# ── Helpers ───────────────────────────────────────────────────────────────────

def _maf_agent_mock(return_text: str):
    """Create a mock MAF agent whose run() returns ``return_text``."""
    agent = MagicMock()
    agent.run = AsyncMock(return_value=return_text)
    session = MagicMock()
    session.state = {}
    agent.create_session = MagicMock(return_value=session)
    return agent


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
    assert classify_intent(text) == expected


# ── Planner ───────────────────────────────────────────────────────────────────

def test_build_plan_ingest():
    agents = [s.agent for s in build_plan(Intent.INGEST)]
    assert "ingestion" in agents
    assert "validator" in agents


def test_build_plan_synthesize():
    assert any(s.agent == "synthesis" for s in build_plan(Intent.SYNTHESIZE))


def test_build_plan_kgc():
    agents = [s.agent for s in build_plan(Intent.KGC)]
    assert "kgc" in agents
    assert "synthesis" in agents


# ── Analyst Agent ─────────────────────────────────────────────────────────────

_FAKE_RETRIEVAL = {
    "has_documents": True,
    "context_message": "Hevolus is a company specialising in AR enterprise solutions.",
    "sources": [],
}


@pytest.mark.asyncio
async def test_analyst_agent_returns_answer():
    mock_agent = _maf_agent_mock("Hevolus è una società specializzata in AR enterprise.")
    with (
        patch("agents.analyst.kg_retrieve_context_tool", new=AsyncMock(return_value=_FAKE_RETRIEVAL)),
        patch("agents.analyst.create_analyst_agent", return_value=mock_agent),
    ):
        from agents.analyst import run_analyst
        result = await run_analyst("cosa sai su Hevolus?", "default")
    assert "Hevolus" in result
    mock_agent.run.assert_called_once()


@pytest.mark.asyncio
async def test_analyst_session_thread_id():
    """session.state must contain thread_id before agent.run() is called."""
    captured: dict = {}

    mock_agent = MagicMock()
    session = MagicMock()
    session.state = {}
    mock_agent.create_session = MagicMock(return_value=session)

    async def capture_run(message, *, session):
        captured.update(session.state)
        return "answer"

    mock_agent.run = capture_run

    with (
        patch("agents.analyst.kg_retrieve_context_tool", new=AsyncMock(return_value=_FAKE_RETRIEVAL)),
        patch("agents.analyst.create_analyst_agent", return_value=mock_agent),
    ):
        from agents.analyst import run_analyst
        await run_analyst("test query", "my-namespace")

    assert captured.get("thread_id") == "my-namespace"


# ── Ingestion Agent ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingestion_agent_success():
    mock_agent = _maf_agent_mock(
        "Documento 'doc.pdf' ingestito con successo.\n- Chunks processati: 45"
    )
    with patch("agents.ingestion.create_ingestion_agent", return_value=mock_agent):
        from agents.ingestion import run_ingestion
        result = await run_ingestion("carica /data/doc.pdf", "default")
    assert len(result) > 0


# ── Validator Agent ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_validator_quality_report():
    """compute_quality_report returns correct metrics from Cypher results."""
    responses = [
        {"results": [{"orphan_count": 3}]},
        {"results": [{"node_count": 50}]},
        {"results": [{"rel_count": 120}]},
        {"results": [{"no_embed_count": 5}]},
    ]
    call_count = 0

    async def fake_cypher(query, namespace, params=None):
        nonlocal call_count
        resp = responses[call_count % len(responses)]
        call_count += 1
        return resp

    with patch("agents.validator.kg_cypher_tool", side_effect=fake_cypher):
        from agents.validator import compute_quality_report
        report = await compute_quality_report("default")

    assert report.total_nodes == 50
    assert report.total_relations == 120
    assert report.orphan_nodes == 3
    assert report.overall_health > 0


# ── Orchestrator dispatch ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_orchestrator_dispatch_query():
    with patch("agents.orchestrator.run_analyst", new=AsyncMock(return_value="Answer")):
        from agents.orchestrator import dispatch
        result = await dispatch("cosa sai su Hevolus?", "default")
    assert result.intent == Intent.QUERY
    assert "analyst" in result.steps


@pytest.mark.asyncio
async def test_orchestrator_dispatch_ingest():
    with (
        patch("agents.orchestrator.run_ingestion", new=AsyncMock(return_value="Ingestito")),
        patch("agents.orchestrator.run_validator", new=AsyncMock(return_value=("QR", None))),
    ):
        from agents.orchestrator import dispatch
        result = await dispatch("carica il documento", "default", context={"file_path": "/tmp/x.pdf"})
    assert result.intent == Intent.INGEST
    assert "ingestion" in result.steps
    assert "validator" in result.steps


@pytest.mark.asyncio
async def test_orchestrator_shim_plan_ingest():
    from agents.orchestrator import orchestrator_node
    state = {
        "user_request": "carica il documento report.pdf",
        "intent": None, "plan": [], "current_step": 0,
        "context": {}, "final_output": None, "error": None,
        "thread_id": "default", "run_id": "run-005",
    }
    result = await orchestrator_node(state)
    assert result["intent"] == Intent.INGEST.value
    assert any(s["agent"] == "ingestion" for s in result["plan"])


@pytest.mark.asyncio
async def test_orchestrator_shim_plan_query():
    from agents.orchestrator import orchestrator_node
    state = {
        "user_request": "cosa sai su intelligenza artificiale?",
        "intent": None, "plan": [], "current_step": 0,
        "context": {}, "final_output": None, "error": None,
        "thread_id": "default", "run_id": "run-006",
    }
    result = await orchestrator_node(state)
    assert result["intent"] == Intent.QUERY.value
    assert any(s["agent"] == "analyst" for s in result["plan"])
