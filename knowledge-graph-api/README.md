# knowledge-graph-api

REST API backend for the **Knowledge Graph Lab** project.
Handles document ingestion pipeline, Redis vector store, Neo4j graph database and hybrid RAG queries.

> Full project documentation in the [root README](../README.md).

---

## Table of contents

- [Stack](#stack)
- [Prerequisites](#prerequisites)
- [Local setup](#local-setup)
- [Configuration](#configuration)
- [Running](#running)
- [Endpoints](#endpoints)
- [Pipelines](#pipelines)
- [Testing and linting](#testing-and-linting)
- [Docker](#docker)
- [Directory structure](#directory-structure)

---

## Stack

| Component | Technology |
| --- | --- |
| Framework | FastAPI 0.115+ + uvicorn |
| Data models | Pydantic v2 + pydantic-settings |
| Graph DB | Neo4j 5.18 (async driver) |
| Vector store | Redis Stack (RedisSearch + RedisJSON) |
| LLM / Embedding | Ollama (llama3 + nomic-embed-text) |
| Logging | structlog (JSON in prod, console in dev) |
| Testing | pytest + pytest-asyncio + pytest-mock |
| Linting | ruff |

---

## Prerequisites

- Python 3.11+
- Neo4j, Redis Stack and Ollama reachable

Start infrastructure via Docker (from the repo root):

```bash
make up-infra
# or:
docker compose --profile dev up -d
```

---

## Local setup

```bash
cd knowledge-graph-api

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Copy `.env.example` from the repo root and customise the values.
For local development use `localhost` instead of Docker container names:

| Variable | Local dev | Docker |
| --- | --- | --- |
| `NEO4J_URI` | `bolt://localhost:7687` | `bolt://neo4j:7687` |
| `REDIS_URL` | `redis://localhost:6379` | `redis://redis:6379` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | `http://ollama:11434` |
| `NEO4J_PASSWORD` | value in `.env` | value in `.env` |
| `LOG_LEVEL` | `DEBUG` | `INFO` |
| `DEBUG` | `true` | `false` |

See [`.env.example`](../.env.example) for the full list.

---

## Running

```bash
# With hot-reload
uvicorn api.main:app --reload --port 8000

# Or from the repo root
make run
```

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check (Neo4j + Redis + Ollama) |
| `POST` | `/ingest` | Ingest a document (PDF, DOCX, TXT) |
| `POST` | `/query` | Hybrid RAG query (JSON response) |
| `POST` | `/query/stream` | RAG query (SSE streaming) |
| `DELETE` | `/documents/{id}` | Delete a document from Redis |
| `GET` | `/documents/{namespace}` | List documents in a namespace |
| `POST` | `/graph/nodes/search` | Search nodes by name + namespace |
| `POST` | `/graph/traverse` | Traverse neighbours up to `max_hops` |
| `POST` | `/graph/cypher` | Read-only Cypher query |

### Example — Ingest

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/data/doc.pdf", "thread_id": "project1", "skip_existing": true}'
```

### Example — RAG query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Neo4j?", "thread_id": "project1", "top_k": 5, "max_hops": 2}'
```

---

## Pipelines

### Ingestion

```text
Document
  [1] File Routing        → MIME type detection (PDF / DOCX / TXT)
  [2] Content Extraction  → raw text + page count
  [3] Text Chunking       → 1024-char chunks, 128-char overlap
  [4] Embedding           → 768-D vectors via Ollama (nomic-embed-text)
  [5] Deduplication       → SHA-256 hash, skip existing chunks
  [6] Entity Extraction   → LLM extracts entities and relations
  [7] Vector Storage      → upsert into Redis (RedisSearch)
  [8] Graph Storage       → nodes and edges in Neo4j (MERGE/upsert)
```

### RAG Query

```text
Question
  [1] Intent Classification → document / entity / relation / general
  [2] Vector Search         → top-K cosine similarity (Redis KNN)
  [3] Graph Enrichment      → neighbour traversal (Neo4j Cypher)
  [4] Context Assembly      → prompt with chunks + nodes + edges
  [5] LLM Generation        → JSON response or SSE stream
```

---

## Testing and linting

```bash
cd knowledge-graph-api

pytest tests/ -v           # all tests (uses mocks, no live services needed)
pytest tests/ -v --cov=.   # with coverage report
ruff check .               # lint
ruff check . --fix         # auto-fix
```

From the repo root:

```bash
make test
make lint
```

---

## Docker

Image: `infra/docker/Dockerfile` (python:3.11-slim, port 8000).

```bash
# Start via compose (prod profile)
docker compose --profile prod up api -d

# Rebuild a single service
docker compose up --build api -d

# Follow logs
docker compose logs -f api
```

---

## Directory structure

```text
knowledge-graph-api/
├── api/
│   ├── main.py                 # FastAPI app, CORS, lifespan
│   ├── schemas.py              # Pydantic request/response models
│   └── routes/
│       ├── ingest.py           # POST /ingest
│       ├── query.py            # POST /query, /query/stream
│       ├── documents.py        # DELETE/GET /documents
│       └── graph.py            # POST /graph/*
├── config/
│   └── settings.py             # Centralised configuration (pydantic-settings)
├── models/
│   ├── base.py                 # VectorDocument
│   ├── graph_node.py           # GraphNode
│   └── relation.py             # Relation
├── pipeline/
│   ├── ingest.py               # Ingestion orchestrator
│   ├── router.py               # MIME-type routing
│   ├── content_extractor.py    # PDF / DOCX / TXT extraction
│   ├── chunker.py              # Text chunking with overlap
│   ├── embedder.py             # Embedding via Ollama
│   └── extractor.py            # Entity/relation extraction (LLM)
├── query/
│   ├── rag_pipeline.py         # RAG orchestrator
│   ├── vector_search.py        # KNN search in Redis
│   └── graph_traversal.py      # Neighbour traversal in Neo4j
├── storage/
│   ├── neo4j_graph.py          # Async Neo4j driver
│   └── redis_vector.py         # RedisSearch vector store
├── utils/
│   ├── logger.py               # structlog configuration
│   └── helpers.py              # SHA-256 hash utility
├── tests/                      # Test suite (mocked Neo4j / Redis / Ollama)
├── scripts/
│   ├── seed_data.py            # Populate DB with sample data
│   └── demo_query.py           # RAG query demo
├── infra/docker/Dockerfile
├── requirements.txt
└── Makefile
```
