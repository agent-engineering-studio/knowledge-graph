# knowledge-graph-agents

**Multi-agent orchestration** layer for the **Knowledge Graph Lab** project.
LangGraph `StateGraph` with a Supervisor + Specialists pattern: an Orchestrator classifies the intent and delegates to 6 specialised agents that interact with the backend via HTTP.

> Full project documentation in the [root README](../README.md).

---

## Table of contents

- [Architecture](#architecture)
- [Stack](#stack)
- [Prerequisites](#prerequisites)
- [Local setup](#local-setup)
- [Configuration](#configuration)
- [Running](#running)
- [Agent API](#agent-api)
- [Agents](#agents)
- [LangGraph orchestration](#langgraph-orchestration)
- [Memory](#memory)
- [Testing](#testing)
- [Docker](#docker)
- [Directory structure](#directory-structure)

---

## Architecture

```text
User request
      |
      v
┌─────────────────┐
│   ORCHESTRATOR  │  classifies intent (regex, 8 intents)
│  Router+Planner │  builds an execution plan
└────────┬────────┘
         │  LangGraph conditional edges
   ┌─────┴──────────────────────────┐
   │                                │
┌──▼──────┐  ┌─────────┐  ┌────────▼────┐
│INGESTION│  │ ANALYST │  │  SYNTHESIS  │
│  AGENT  │  │  AGENT  │  │    AGENT    │
└──┬──────┘  └────┬────┘  └──────┬──────┘
   │              │              │
┌──▼──────┐  ┌────▼────┐  ┌──────▼──────┐
│VALIDATOR│  │   KGC   │  │   MONITOR   │
│  AGENT  │  │  AGENT  │  │    AGENT    │
└─────────┘  └─────────┘  └─────────────┘
                   │ HTTP REST
          ┌────────▼─────────┐
          │ knowledge-graph  │
          │      -api        │
          │  Neo4j + Redis   │
          └──────────────────┘
```

---

## Stack

| Component | Technology |
| --- | --- |
| Orchestration | LangGraph 0.2+ (StateGraph + conditional routing) |
| Agent framework | LangChain 0.3+ |
| REST API | FastAPI 0.115+ + uvicorn |
| HTTP client | httpx 0.27+ (calls to knowledge-graph-api) |
| Data models | Pydantic v2 |
| LLM | Ollama (llama3, via direct httpx) |
| Testing | pytest + pytest-asyncio |
| Linting | ruff |

---

## Prerequisites

- Python 3.11+
- `knowledge-graph-api` running at `http://localhost:8000`
- Ollama reachable at `http://localhost:11434`

Start infrastructure + API (from the repo root):

```bash
make up-infra   # Neo4j + Redis + Ollama
make run        # knowledge-graph-api on port 8000
```

---

## Local setup

```bash
cd knowledge-graph-agents

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Or from the repo root
make agents-install
```

---

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `KG_API_URL` | `http://localhost:8000` | FastAPI backend URL |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama base URL |
| `OLLAMA_LLM_MODEL` | `llama3` | LLM model for generation |
| `KG_API_TIMEOUT` | `60` | HTTP timeout in seconds |

```bash
cp .env.example .env   # then edit as needed
```

---

## Running

```bash
# With hot-reload (port 8001)
uvicorn api.agent_api:app --reload --port 8001

# Or from the repo root
make agents-run
```

- Agent API: `http://localhost:8001`
- Swagger UI: `http://localhost:8001/docs`

> In Docker the internal port 8001 is mapped to host port 8002 to avoid a conflict with RedisInsight.

---

## Agent API

### `POST /agents/run`

Execute the multi-agent workflow for a natural-language request.

```bash
curl -X POST http://localhost:8001/agents/run \
  -H "Content-Type: application/json" \
  -d '{"request": "What do you know about Neo4j?", "thread_id": "default"}'
```

**Request body:**

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `request` | string | required | Natural-language request |
| `thread_id` | string | `default` | KG namespace to operate on |
| `context` | dict | `{}` | Extra params (e.g. `file_path`, `topic`) |

**Response** (`AgentRunResponse`):

```json
{
  "run_id": "uuid",
  "intent": "query",
  "output": "Neo4j is a graph database...",
  "plan": [{"agent": "analyst", "action": "hybrid_search", "status": "done"}],
  "quality": {"overall_health": 0.85},
  "duration_ms": 2340,
  "error": null
}
```

### `GET /agents/run/{run_id}`

Retrieve the record of a previous run.

### `GET /agents/runs`

List the last N runs (default 20), ordered by date descending.

### `GET /agents/health`

```json
{ "status": "ok", "kg_api": true, "kg_api_url": "http://localhost:8000" }
```

---

## Agents

| Agent | Activated intents | Responsibility |
| --- | --- | --- |
| **Orchestrator** | all | Classifies intent, builds plan — never calls tools directly |
| **Ingestion** | `ingest` | Health check, dedup, `kg_ingest`, report |
| **Analyst** | `query`, `analyze` | Vector / graph / hybrid search (3 strategies) |
| **Validator** | `validate` | 4 Cypher queries, `KGQualityReport` with `overall_health` |
| **KGC** | `kgc` | Transitive closure + similarity, proposes missing relations |
| **Synthesis** | `synthesize` | RAG context + Ollama, Markdown report (optional auto-ingest) |
| **Monitor** | `monitor`, `health` | Health check + quality alert summary |

### Intent classification

| Keywords in request | Intent | Agent |
| --- | --- | --- |
| ingest, upload, load | `ingest` | Ingestion |
| what do you know, describe, tell me | `query` | Analyst |
| analyse, count, statistics | `analyze` | Analyst |
| report, generate, summarise | `synthesize` | Synthesis |
| validate, quality check | `validate` | Validator |
| missing relations, gap | `kgc` | KGC |
| health, status, monitor | `monitor` | Monitor |

---

## LangGraph orchestration

The `StateGraph` is defined in `orchestration/graph.py`:

```text
START → orchestrator → [route_by_intent] → specialised_agent → END
```

Conditional routing:

- `ingest` → `ingestion` → `validator`
- `kgc` → `kgc` → `synthesis`
- all others → `END`

Shared state (`AgentState`) flows through all nodes as a `TypedDict`:

```python
class AgentState(TypedDict):
    request: str
    thread_id: str
    intent: Intent
    plan: list[AgentStep]
    context: dict
    output: str
    error: str | None
    quality: dict
```

---

## Memory

Each run produces an `AgentRunRecord` (Pydantic) saved in two places:

1. **In-process store** (`dict`) — always available, reset on restart
2. **Neo4j** (best-effort) — `AgentRun` node via `POST /graph/cypher/write`

```cypher
MATCH (r:AgentRun {run_id: $run_id})
RETURN r.agent_name, r.intent, r.status, r.duration_ms
```

---

## Testing

```bash
cd knowledge-graph-agents

pytest tests/ -v

# Or from the repo root
make agents-test
```

8 tests with mocked `httpx` — no live services needed.
Coverage: intent classification, planner, async agents, error handling.

---

## Docker

```bash
# Start via compose (prod profile) — host port 8002
docker compose --profile prod up agents -d

# Follow logs
docker compose logs -f agents

# Health check
curl http://localhost:8002/agents/health
```

---

## Directory structure

```text
knowledge-graph-agents/
├── agents/
│   ├── orchestrator.py         # Router + Planner (intent → plan)
│   ├── ingestion.py            # Ingestion Agent
│   ├── analyst.py              # Analyst Agent (3 strategies)
│   ├── validator.py            # Validator Agent (KGQualityReport)
│   ├── kgc.py                  # KGC Agent (missing relations)
│   ├── synthesis.py            # Synthesis Agent (Ollama report)
│   └── monitor.py              # Monitor Agent (health + alerts)
├── orchestration/
│   ├── state.py                # AgentState, Intent, AgentStep
│   ├── router.py               # Intent classification (regex)
│   ├── planner.py              # build_plan() per intent
│   └── graph.py                # StateGraph + conditional routing
├── tools/
│   └── kg_tools.py             # 8 async HTTP wrappers for kg-api
├── memory/
│   └── kg_memory.py            # AgentRunRecord + in-process store + Neo4j
├── api/
│   └── agent_api.py            # FastAPI app (port 8001)
├── tests/
│   ├── conftest.py
│   └── test_agents.py
├── Dockerfile
├── requirements.txt
├── pyproject.toml              # asyncio_mode = "auto"
└── .env.example
```
