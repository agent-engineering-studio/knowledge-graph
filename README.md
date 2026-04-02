# Knowledge Graph Lab

![banner_wide_en](https://github.com/user-attachments/assets/fbe6ad06-2ffd-4cb7-a958-8defe686cb10)

Complete **Knowledge Graph** system with document ingestion pipeline, vector store, graph database, hybrid RAG, web interface and a **multi-agent** orchestration layer built on LangGraph.
Companion project for the book _"Knowledge Graph: dalla Teoria alla Pratica v2"_ (Giuseppe Zileni - Hevolus Innovation, 2026).

---

## Table of contents

- [Modules](#modules)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [System requirements](#system-requirements)
- [Quick start](#quick-start)
- [Local development (without Docker)](#local-development-without-docker)
- [Running with Docker](#running-with-docker)
- [Repository structure](#repository-structure)
- [API Reference](#api-reference)
- [Agent API Reference](#agent-api-reference)
- [Multi-Agent system](#multi-agent-system)
- [UI (Frontend)](#ui-frontend)
- [Environment variables](#environment-variables)
- [Debugging with VS Code](#debugging-with-vs-code)
- [Testing and linting](#testing-and-linting)
- [Ingestion pipeline](#ingestion-pipeline)
- [RAG pipeline (query)](#rag-pipeline-query)
- [Data models](#data-models)
- [Scientific references](#scientific-references)
- [Troubleshooting](#troubleshooting)

---

## Modules

| Module | Description | README |
| --- | --- | --- |
| [knowledge-graph-api](knowledge-graph-api/) | FastAPI backend — ingestion, RAG, graph | [README](knowledge-graph-api/README.md) |
| [knowledge-graph-ui](knowledge-graph-ui/) | Next.js 15 web frontend | [README](knowledge-graph-ui/README.md) |
| [knowledge-graph-mcp](knowledge-graph-mcp/) | MCP server — exposes API as LLM tools | [README](knowledge-graph-mcp/README.md) |
| [knowledge-graph-agents](knowledge-graph-agents/) | Multi-agent orchestration (LangGraph) | [README](knowledge-graph-agents/README.md) |

---

## Architecture

```text
  Client / LLM Host (Claude Desktop, VS Code, custom app)
         |                            |
         | MCP Protocol               | HTTP REST
         v                            v
  +------------------+      +--------------------+
  | knowledge-graph  |      |  knowledge-graph   |
  |      -mcp        |      |      -agents       |
  | (MCP tool layer) |      | (Multi-Agent API)  |
  | localhost:8080   |      | localhost:8002     |
  +--------+---------+      +--------+-----------+
           |                         |
           +----------+--------------+
                      | HTTP REST
             +--------v---------+
             |   FastAPI API    |
             | knowledge-graph  |
             |      -api        |
             |  localhost:8000  |
             +--+-----+------+--+
                |     |      |
   +------------+  +--+--+  ++-----------+
   |               |     |               |
+--v------------+ +v----v--+ +----------v-----+
| Neo4j 5.18   | | Redis   | | Ollama         |
| Graph DB     | | Stack   | | llama3 +       |
| :7474 / :7687| | :6379   | | nomic-embed    |
+--------------+ | :8001   | | :11434         |
                 +---------+ +----------------+
                      ^
             +--------+---------+
             |   Next.js UI     |
             | knowledge-graph  |
             |      -ui         |
             |  localhost:3000  |
             +------------------+
```

Data flows through three main paths:

1. **Ingestion**: document → chunking → embedding (Ollama) → dedup (SHA-256) → entity/relation extraction (LLM) → storage in Redis (vectors) + Neo4j (graph)
2. **RAG Query**: question → intent classification → vector search (Redis) → graph traversal (Neo4j) → context assembly → LLM generation (Ollama) → answer
3. **Multi-Agent**: request → Orchestrator (LangGraph) → specialised agent → HTTP tools to API → structured response

---

## Tech stack

| Component | Technology | Version |
| --- | --- | --- |
| **Graph Database** | Neo4j (Cypher + APOC) | 5.18 |
| **Vector Store** | Redis for AI (RedisSearch + RedisJSON) | latest |
| **LLM Inference** | Ollama (local, no API key) | latest |
| **LLM Model** | Llama 3 | latest |
| **Embedding Model** | nomic-embed-text (768 dim) | latest |
| **REST API** | FastAPI + uvicorn | 0.115+ |
| **Data Models** | Pydantic v2 + pydantic-settings | 2.7+ |
| **Multi-Agent** | LangGraph (StateGraph + routing) | 0.2+ |
| **Frontend** | Next.js + React + Tailwind CSS | 15 / 19 / 4 |
| **Graph Visualisation** | react-force-graph-2d | 1.26+ |
| **Logging** | structlog (JSON in prod, console in dev) | 24.1+ |
| **Testing** | pytest + pytest-asyncio + pytest-mock | 8.2+ |
| **Linting** | ruff (API/Agents), ESLint + next lint (UI) | 0.4+ |
| **Containerisation** | Docker + Docker Compose | 24+ / v2 |

---

## System requirements

- **Docker 24+** and Docker Compose v2
- **8 GB RAM** recommended (Ollama + Neo4j + Redis)
- **Python 3.11+** (only for local API development without Docker)
- **Node.js 22+** (only for local UI development without Docker)
- NVIDIA GPU optional (to accelerate Ollama)

---

## Quick start

The fastest way to get everything running:

```bash
# 1. Clone and move into the root
git clone <repo-url>
cd knowledge-graph

# 2. Configure environment variables
cp .env.example .env
# Edit NEO4J_PASSWORD and other values in .env

# 3. Start all services (production stack)
make up-prod

# 4. Download Ollama models (first time only)
make pull-models

# 5. (Optional) Seed with sample data
cd knowledge-graph-api && make seed

# 6. Open in the browser
#    UI:            http://localhost:3000
#    API Swagger:   http://localhost:8000/docs
#    Agent API:     http://localhost:8002/docs
#    Neo4j:         http://localhost:7474
#    RedisInsight:  http://localhost:8001
```

---

## Local development (without Docker)

Run only the infrastructure in Docker and the application servers natively for a hot-reload development experience.

### 1. Infrastructure (Neo4j + Redis + Ollama + RedisInsight)

```bash
cd knowledge-graph
make up-dev
# or: docker compose --profile dev up -d
```

Wait for services to become healthy:

```bash
docker compose ps
```

### 2. Ollama models (first time only)

```bash
make pull-models
```

### 3. API (FastAPI)

```bash
cd knowledge-graph-api

python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000
```

API available at `http://localhost:8000`. Interactive Swagger docs at `http://localhost:8000/docs`.

### 4. Agents (Multi-Agent API)

```bash
cd knowledge-graph-agents

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
uvicorn api.agent_api:app --reload --port 8001
```

Agent API available at `http://localhost:8001`. Swagger at `http://localhost:8001/docs`.

```bash
# Example call
curl -X POST http://localhost:8001/agents/run \
  -H "Content-Type: application/json" \
  -d '{"request": "What do you know about Neo4j?", "thread_id": "default"}'
```

### 5. UI (Next.js)

```bash
cd knowledge-graph-ui

cp .env.local.example .env.local
# Verify NEXT_PUBLIC_API_URL=http://localhost:8000

npm install
npm run dev
```

UI available at `http://localhost:3000`.

---

## Running with Docker

### Docker Compose profiles

The stack uses Docker Compose profiles to separate environments:

| Profile | Services started | Use case |
| --- | --- | --- |
| `dev` | neo4j, redis, ollama, redisinsight | Local development — run apps outside Docker |
| `prod` | neo4j, redis, ollama, api, ui, mcp, agents | Full production stack |

### Makefile targets

```bash
make up-dev     # infrastructure + RedisInsight (profile dev)
make up-prod    # full production stack (profile prod)
make down       # stop all services
make pull-models  # download llama3 + nomic-embed-text
```

### Production

```bash
cp .env.example .env
# Configure .env with real passwords

make up-prod
```

Services exposed:

| Service | URL | Description |
| --- | --- | --- |
| UI | <http://localhost:3000> | Next.js frontend |
| API | <http://localhost:8000> | FastAPI REST API |
| API Docs | <http://localhost:8000/docs> | Swagger UI (API) |
| Agent API | <http://localhost:8002> | Multi-Agent Orchestration API |
| Agent Docs | <http://localhost:8002/docs> | Swagger UI (Agent API) |
| MCP Server | <http://localhost:8080> | MCP tool layer (SSE transport) |
| Neo4j Browser | <http://localhost:7474> | Neo4j web interface |
| RedisInsight | <http://localhost:8001> | Redis web interface (built-in) |
| Ollama | <http://localhost:11434> | Ollama API |

### Development (infra only)

```bash
make up-dev
```

This starts only Neo4j, Redis, Ollama and a standalone RedisInsight on port 5540.
Run API, UI, Agents and MCP locally with hot-reload (see [Local development](#local-development-without-docker)).

Additional services when using `--profile dev`:

| Service | URL | Description |
| --- | --- | --- |
| RedisInsight | <http://localhost:5540> | Standalone Redis UI (profile dev) |
| Neo4j Browser | <http://localhost:7474> | Built into neo4j container |

### Useful Docker commands

```bash
# Service status
docker compose ps

# Follow logs of a specific service
docker compose logs -f api
docker compose logs -f ui

# Stop all services
make down

# Stop and remove volumes (WARNING: deletes all Neo4j/Redis data)
docker compose down -v

# Rebuild a single service
docker compose up --build api -d
```

### NVIDIA GPU (optional)

GPU acceleration for Ollama is configured in `docker-compose.yml` under the `deploy` section of the `ollama` service — it is enabled by default and requires the NVIDIA Container Toolkit.

---

## Repository structure

```text
knowledge-graph/
├── .vscode/                        # VS Code configuration (debug, tasks, settings)
│   ├── launch.json                 # Debug configurations
│   ├── tasks.json                  # Build/run tasks
│   └── settings.json               # Editor settings
├── docker-compose.yml              # Full stack (profiles: dev, prod)
├── Makefile                        # Shorthand commands
├── .env.example                    # Environment variable template
│
├── knowledge-graph-api/            # Backend API (Python / FastAPI)
│   ├── api/                        # FastAPI app, routes, schemas
│   │   ├── main.py                 # Application entry point
│   │   ├── schemas.py              # Pydantic request/response models
│   │   └── routes/
│   │       ├── ingest.py           # POST /ingest
│   │       └── query.py            # POST /query, POST /query/stream
│   ├── config/
│   │   └── settings.py             # Centralised configuration (pydantic-settings)
│   ├── models/                     # Domain models
│   │   ├── base.py                 # VectorDocument
│   │   ├── graph_node.py           # GraphNode (KGNode)
│   │   └── relation.py             # Relation
│   ├── pipeline/                   # Ingestion pipeline
│   ├── query/                      # Query pipeline
│   ├── storage/                    # Persistence backends
│   ├── infra/docker/Dockerfile     # API Dockerfile
│   └── requirements.txt
│
├── knowledge-graph-agents/         # Multi-Agent Orchestration (Python / LangGraph)
│   ├── agents/                     # Specialised agents
│   ├── orchestration/              # LangGraph workflow
│   ├── tools/kg_tools.py           # Async HTTP wrappers for the API
│   ├── memory/kg_memory.py         # AgentRunRecord + in-process store
│   ├── api/agent_api.py            # FastAPI app port 8001 (host 8002 in Docker)
│   ├── Dockerfile
│   └── requirements.txt
│
├── knowledge-graph-mcp/            # MCP Server (Python / FastMCP)
│   ├── src/kg_mcp/
│   │   ├── server.py               # MCP server + tool definitions
│   │   ├── api_client.py           # HTTP client to the API
│   │   └── tools.py                # 8 tool implementations
│   ├── Dockerfile
│   └── pyproject.toml
│
└── knowledge-graph-ui/             # Frontend (Next.js / React)
    ├── src/
    │   ├── app/                    # Next.js App Router pages
    │   ├── components/             # Reusable React components
    │   └── lib/api-client.ts       # Typed fetch wrapper
    ├── Dockerfile
    └── package.json
```

---

## API Reference

Interactive OpenAPI documentation generated automatically by FastAPI:

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>
- **OpenAPI JSON**: <http://localhost:8000/openapi.json>

### Endpoints

#### `GET /health` — Health check

Checks connectivity with Neo4j, Redis and Ollama.

**Response** (`HealthResponse`):

```json
{
  "status": "healthy",
  "neo4j": true,
  "redis": true,
  "ollama": true
}
```

`status` is `"healthy"` when all services are reachable, `"degraded"` otherwise.

---

#### `POST /ingest` — Document ingestion

Uploads a document, processes it through the full pipeline (chunking, embedding, entity extraction) and persists it in Redis and Neo4j.

**Request body** (`IngestRequest`):

```json
{
  "file_path": "/path/to/document.pdf",
  "thread_id": "my-project",
  "skip_existing": true
}
```

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `file_path` | string | required | Path to the file to process (PDF, DOCX, TXT) |
| `thread_id` | string | required | Namespace for multi-tenant isolation |
| `skip_existing` | boolean | `true` | Skip already-indexed chunks (dedup via SHA-256) |

**Response** (`IngestResult`):

```json
{
  "document_id": "a1b2c3d4-...",
  "chunks_processed": 15,
  "chunks_skipped": 0,
  "entities_extracted": 23,
  "relations_extracted": 18,
  "nodes_created": 23,
  "edges_created": 18,
  "processing_time_ms": 12450.5,
  "errors": []
}
```

Supported formats: `.pdf` (pypdf), `.docx` (python-docx), `.txt` (plain text).

---

#### `POST /query` — RAG query (synchronous)

Executes a hybrid RAG query: vector search + graph traversal + LLM generation.

**Request body** (`QueryRequest`):

```json
{
  "query": "Which technologies are connected to Neo4j?",
  "thread_id": "my-project",
  "top_k": 10,
  "max_hops": 2
}
```

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `query` | string | required | Natural-language question |
| `thread_id` | string | required | Namespace to query |
| `top_k` | integer | `10` | Number of vector search results |
| `max_hops` | integer | `2` | Maximum graph traversal depth |

**Response** (`RAGResponse`):

```json
{
  "answer": "Neo4j is connected to...",
  "sources": [
    { "doc_id": "chunk-uuid", "text_preview": "First 200 chars...", "score": 0.876 }
  ],
  "nodes_used": ["node-id-1"],
  "edges_used": ["NodeA --USES--> NodeB"],
  "query_intent": "entity_query",
  "processing_time_ms": 3200.0
}
```

`query_intent` can be: `document_query`, `entity_query`, `relation_query`, `general`.

---

#### `POST /query/stream` — RAG query (SSE streaming)

Same request as `/query`, but the response is a stream of Server-Sent Events. Each LLM token is sent as an event:

```text
data: Neo4j
data:  is
data:  connected
data:  to...
data: [DONE]
```

On error: `data: [ERROR] message`.

---

#### `DELETE /documents/{document_id}` — Delete document

Removes a document and all its chunks from Redis.

**Response**:

```json
{ "deleted": "a1b2c3d4-..." }
```

---

## Agent API Reference

The Agent API exposes the multi-agent system at `http://localhost:8002` (internal port 8001).

- **Swagger UI**: <http://localhost:8002/docs>

### Agent Endpoints

#### `POST /agents/run` — Execute multi-agent workflow

Receives a natural-language request, classifies the intent, executes the agent plan and returns structured output.

**Request body**:

```json
{
  "request": "What do you know about Neo4j?",
  "thread_id": "default",
  "context": {}
}
```

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
  "quality": {"overall_health": 0.85, "total_nodes": 120},
  "duration_ms": 2340,
  "error": null
}
```

**Automatically classified intents**:

| Keywords in request | Intent | Delegated agent |
| --- | --- | --- |
| ingest, upload, load | `ingest` | Ingestion Agent |
| what do you know, describe, tell me | `query` | Analyst Agent |
| analyse, count, statistics | `analyze` | Analyst Agent |
| report, generate, summarise | `synthesize` | Synthesis Agent |
| validate quality, check | `validate` | Validator Agent |
| missing relations, gap | `kgc` | KGC Agent |
| health, status, monitor | `monitor` | Monitor Agent |

---

#### `GET /agents/run/{run_id}` — Retrieve a run

Returns the persisted record of a previous execution.

---

#### `GET /agents/runs` — List recent runs

Returns the last N runs (default 20), ordered by date descending.

---

#### `GET /agents/health` — Agent API health check

```json
{ "status": "ok", "kg_api": true, "kg_api_url": "http://localhost:8000" }
```

---

## Multi-Agent system

The `knowledge-graph-agents/` module implements the **Supervisor + Specialists** pattern.

### Internal architecture

```text
                    ┌──────────────────┐
                    │   ORCHESTRATOR   │
                    │  (Router+Planner)│
                    └────────┬─────────┘
                             │  delegates by intent (LangGraph)
          ┌──────────────────┼──────────────────┐
          │                  │                  │
   ┌──────▼──────┐   ┌───────▼──────┐   ┌──────▼──────┐
   │  INGESTION  │   │   ANALYST    │   │  SYNTHESIS  │
   │   AGENT     │   │    AGENT     │   │    AGENT    │
   └──────┬──────┘   └───────┬──────┘   └──────┬──────┘
          │                  │                  │
   ┌──────▼──────┐   ┌───────▼──────┐   ┌──────▼──────┐
   │  VALIDATOR  │   │     KGC      │   │   MONITOR   │
   │   AGENT     │   │    AGENT     │   │    AGENT    │
   └─────────────┘   └──────────────┘   └─────────────┘
                             │ HTTP REST
                    ┌────────▼─────────┐
                    │ knowledge-graph  │
                    │      -api        │
                    │  Neo4j + Redis   │
                    └──────────────────┘
```

### Agents

| Agent | Responsibility |
| --- | --- |
| Orchestrator | Classifies intent, builds plan — never executes tools directly |
| Ingestion | Health check, dedup check, `kg_ingest`, report |
| Analyst | Vector search / graph traversal / hybrid (3 strategies) |
| Validator | 4 Cypher queries, `KGQualityReport` with `overall_health` |
| KGC | Transitive closure + similarity, finds missing relations |
| Synthesis | RAG context + Ollama, Markdown report (optional auto-ingest) |
| Monitor | Health check + quick quality check, alert summary |

### Agent memory

Each execution is recorded as an `AgentRunRecord` (Pydantic) in the in-process store and, best-effort, as an `AgentRun` node in Neo4j via `POST /graph/cypher/write`.

```cypher
MATCH (r:AgentRun {run_id: $run_id})
RETURN r.agent_name, r.intent, r.status, r.duration_ms
```

### Agent tests

```bash
cd knowledge-graph-agents
pytest tests/ -v
```

Tests use `httpx` mocks — no live services needed.

---

## UI (Frontend)

The UI is a Next.js 15 (App Router) SPA with three main pages.

### Dashboard (`/`)

- Real-time service health indicators (Neo4j, Redis, Ollama)
- Quick links to functional pages
- Direct access to Swagger, Neo4j Browser, RedisInsight

### Search / Query (`/query`)

- Search form with configurable parameters (`thread_id`, `top_k`, `max_hops`)
- SSE streaming support: tokens appear in real time during generation
- Structured result view: answer, sources with score, metadata (intent, nodes, edges, time)

### Graph View (`/graph`)

- Query input to explore sections of the knowledge graph
- Interactive force-directed visualisation (react-force-graph-2d)
- Colour-coded nodes by type, edges with arrows and relation labels
- Zoom, pan and drag

### Typed API client

`src/lib/api-client.ts` is the single contract between UI and API:

- TypeScript interfaces mirroring the Pydantic models
- Typed functions for every endpoint (`getHealth`, `postQuery`, `postIngest`, `deleteDocument`)
- Async generator `streamQuery()` for SSE streaming
- `AbortSignal` support for request cancellation

### UI configuration

Copy `.env.local.example` to `.env.local`:

```bash
cd knowledge-graph-ui
cp .env.local.example .env.local
```

| Variable | Default | Description |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API base URL |
| `NEXT_PUBLIC_ENABLE_STREAMING` | `true` | Enable/disable SSE streaming |
| `NEXT_PUBLIC_ENABLE_GRAPH_VIEW` | `true` | Feature flag for graph view |

---

## Environment variables

All variables are defined in `.env.example` at the root. Copy to `.env` and customise:

```bash
cp .env.example .env
```

### Neo4j

| Variable | Default | Description |
| --- | --- | --- |
| `NEO4J_URI` | `bolt://neo4j:7687` | Connection URI (use `localhost` for local dev) |
| `NEO4J_USER` | `neo4j` | Username |
| `NEO4J_PASSWORD` | `yourpassword` | **Change this** in production |
| `NEO4J_DATABASE` | `neo4j` | Database name |

### Redis

| Variable | Default | Description |
| --- | --- | --- |
| `REDIS_URL` | `redis://redis:6379` | Connection URL (use `localhost` for local dev) |
| `REDIS_INDEX_NAME` | `kg_vectors` | Vector index name |
| `REDIS_VECTOR_DIM` | `768` | Vector dimension (depends on embedding model) |

### Ollama

| Variable | Default | Description |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama URL (use `localhost` for local dev) |
| `OLLAMA_LLM_MODEL` | `llama3` | Text generation model |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model (768 dim) |

### Chunking

| Variable | Default | Description |
| --- | --- | --- |
| `CHUNK_SIZE` | `1024` | Maximum chunk size (characters) |
| `CHUNK_OVERLAP` | `128` | Overlap between consecutive chunks (characters) |

### Application

| Variable | Default | Description |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `DEBUG` | `false` | Debug mode |

> **Note**: for local development without Docker, `NEO4J_URI`, `REDIS_URL` and `OLLAMA_BASE_URL` must use `localhost` instead of Docker container names.

---

## Debugging with VS Code

Open the `knowledge-graph/` folder in VS Code. The `.vscode/` directory contains ready-to-use configurations.

### Recommended extensions

- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) (ms-python.python)
- [Ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff) (charliermarsh.ruff)
- [Prettier](https://marketplace.visualstudio.com/items?itemName=esbenp.prettier-vscode) (esbenp.prettier-vscode)
- JavaScript Debugger (built-in)

### Debug configurations (launch.json)

| Name | Type | Description |
| --- | --- | --- |
| **API: FastAPI (debugpy)** | Python | Starts uvicorn with Python debugger, hot-reload |
| **UI: Next.js (Server)** | Node | Starts `npm run dev` and attaches Chrome debugger |
| **UI: Next.js (Chrome)** | Chrome | Attaches to a running Next.js server on :3000 |
| **API: Tests (pytest)** | Python | Runs pytest with step-through debugger |
| **Agents: API (debugpy)** | Python | Starts Agent API with debugger on port 8001 |
| **Agents: Orchestrator (debugpy)** | Python | Runs the LangGraph orchestrator directly |
| **MCP: Server (debugpy)** | Python | Starts the MCP server with debugger |
| **Full Stack: API + UI** | Compound | Starts API + UI in parallel with one click |
| **Full Stack: All Services** | Compound | Starts API + UI + MCP + Agents |

### Recommended workflow

1. Start infrastructure: `make up-dev`
2. In VS Code, select **"Full Stack: API + UI"** in the Run and Debug panel
3. Press `F5` — API (port 8000) and UI (port 3000) start with active debuggers
4. Set breakpoints in Python (API) or TypeScript (UI) code
5. Open `http://localhost:3000` in the browser

### Tasks (tasks.json)

Accessible from `Terminal > Run Task...`:

| Task | Command |
| --- | --- |
| Docker: Up Prod | `docker compose --profile prod up --build -d` |
| Docker: Up Dev (infra + tools) | `docker compose --profile dev up -d` |
| Docker: Down | `docker compose --profile prod --profile dev down` |
| API: Dev Server | `uvicorn api.main:app --reload` |
| UI: Dev Server | `npm run dev` |
| API: Run Tests | `pytest tests/ -v` |
| API: Lint | `ruff check .` |
| Pull Ollama Models | `ollama pull llama3 + nomic-embed-text` |

---

## Testing and linting

### API (Python)

```bash
cd knowledge-graph-api

pytest tests/ -v                        # run all tests
pytest tests/test_ingest.py -v -k "test_name"  # specific test
ruff check .                            # lint
ruff check . --fix                      # auto-fix
```

Tests use mocks for Neo4j, Redis and Ollama — no live services needed.

### Agents (Python)

```bash
cd knowledge-graph-agents

pytest tests/ -v
ruff check .
```

### UI (TypeScript)

```bash
cd knowledge-graph-ui
npm run lint
```

### Makefile targets (from repo root)

```bash
make test           # pytest (API)
make lint           # ruff (API)
make agents-test    # pytest (Agents)
make agents-lint    # ruff (Agents)
make mcp-test       # pytest (MCP)
```

---

## Ingestion pipeline

The ingestion pipeline (`POST /ingest`) processes a document in 8 stages:

```text
Document
    |
    v
[1] File Routing -------> MIME type detection (PDF / DOCX / TXT)
    |
    v
[2] Content Extraction -> Raw text + page count
    |
    v
[3] Text Chunking ------> 1024-char chunks, 128-char overlap
    |                     (respects sentence boundaries)
    v
[4] Embedding ----------> 768-D vectors via Ollama (nomic-embed-text)
    |
    v
[5] Deduplication ------> SHA-256 hash to skip existing chunks
    |
    v
[6] Entity Extraction --> LLM extracts entities (Person, Technology, ...)
    |                     and relations (USES, PART_OF, ...)
    v
[7] Vector Storage -----> Upsert into Redis (RedisSearch + RedisJSON)
    |
    v
[8] Graph Storage ------> Nodes and edges in Neo4j (MERGE/upsert)
```

### Supported entity types

Person, Organization, Product, Technology, Process, Event, Location, Concept, Document, Category, Tag

### Supported relation types

BELONGS_TO, RELATES_TO, CREATED_BY, MENTIONS, PART_OF, USES, LOCATED_IN, OCCURRED_AT, HAS_TAG, SIMILAR_TO, DEPENDS_ON, REPLACED_BY

---

## RAG pipeline (query)

The RAG pipeline (`POST /query`) answers questions in 5 stages:

```text
User question
    |
    v
[1] Intent Classification -> document_query | entity_query
    |                                        | relation_query | general
    v
[2] Vector Search ---------> Top-K documents by cosine similarity
    |                         (Redis KNN)
    v
[3] Graph Enrichment ------> Traversal of neighbours up to max_hops
    |                         (Neo4j Cypher)
    v
[4] Context Assembly ------> System prompt with chunks + nodes + edges
    |
    v
[5] LLM Generation -------> Response (sync JSON or SSE stream)
```

The search is **hybrid**: it combines semantic similarity (vector) with structural relations (graph) to produce more complete and context-aware answers.

---

## Data models

### VectorDocument (Redis)

Each document chunk is stored in Redis as JSON with a vector index:

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Unique chunk identifier |
| `thread_id` | string | Namespace / partition |
| `text` | string | Chunk text content |
| `name` | string | Source filename |
| `vector` | float[768] | Chunk embedding |
| `content_hash` | string | SHA-256 for deduplication |
| `base_document_id` | string | Parent document ID |
| `mime_type` | string | Original file MIME type |
| `page_number` | integer | Page number (PDFs) |

### GraphNode (Neo4j)

Each extracted entity is stored as a node in the graph:

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Unique identifier |
| `name` | string | Entity name |
| `label` | string | Display label |
| `node_type` | string | Type (Person, Technology, ...) |
| `namespace` | string | Namespace / partition |
| `importance` | float | Score 0-1 |
| `confidence` | float | Score 0-1 |
| `source_chunk_ids` | string[] | References to source chunks |

### Relation (Neo4j)

Each extracted relation becomes an edge in the graph:

| Field | Type | Description |
| --- | --- | --- |
| `id` | UUID | Unique identifier |
| `source_id` | string | Source node |
| `target_id` | string | Target node |
| `relation_type` | string | Type (USES, PART_OF, ...) |
| `weight` | float | Relation strength 0-1 |
| `confidence` | float | Extraction confidence 0-1 |

---

## Scientific references

This project draws inspiration from the following pipelines and papers:

| Paper / Tool | Usage in this project |
| --- | --- |
| **OpenIE6** (Kolluru et al., 2020) | Patterns for open-domain triple extraction |
| **CoDe-KG** (Anuyah et al., 2025) | Modular pipeline: coreference + decomposition + RE |
| **KGGen** (Mo et al., 2025) | Entity clustering/dedup to reduce graph sparsity |
| **BLINK** (Wu et al., 2019) | Bi-encoder + cross-encoder architecture for entity linking |
| **DocRED** (Yao et al., 2019) | Benchmark for document-level relation extraction |

Hybrid architecture recommended by the papers: **Graph DB** (Neo4j/Cypher) for structure + **Vector DB** (Redis/FAISS) for semantic similarity, with the option of vector indexes directly in Neo4j (`CREATE VECTOR INDEX`).

---

## Troubleshooting

### Ollama does not start or does not respond

```bash
docker compose logs ollama

# If the container is up but models are not downloaded
docker compose exec ollama ollama list
make pull-models
```

The first query after pulling models may be slow (~30s) due to model loading.

### Neo4j healthcheck fails

```bash
docker compose logs neo4j

# Verify the password matches
echo $NEO4J_PASSWORD   # must match the value in .env
```

### API returns "degraded" on health check

One or more backend services are unreachable. Check which ones return `false`:

```bash
curl http://localhost:8000/health
```

Verify all containers are running: `docker compose ps`

### UI cannot connect to the API

Verify `NEXT_PUBLIC_API_URL` is set correctly in `.env.local`:

- Local dev: `http://localhost:8000`
- Docker: `http://localhost:8000` (the browser calls the API directly)
- Cross-host: configure CORS on the API (currently `allow_origins=["*"]`)

### Memory errors

The full stack requires ~6-8 GB RAM. If Docker has lower limits:

```bash
docker stats

# Use a smaller Ollama model or disable APOC if not needed
```

### Full data reset

```bash
# WARNING: deletes all data!
docker compose down -v
make up-prod
```
