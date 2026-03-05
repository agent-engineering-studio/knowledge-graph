# Knowledge Graph Lab

Sistema completo di Knowledge Graph con pipeline di ingestion, vector store, graph database e pipeline RAG. Progetto companion del libro _"Knowledge Graph: dalla Teoria alla Pratica"_ (Giuseppe Zileni, 2026).

## Stack tecnologico

| Componente       | Tecnologia                                 |
| ---------------- | ------------------------------------------ |
| Graph Database   | **Neo4j 5.18** (Cypher)                    |
| Vector Store     | **Redis for AI** (RedisSearch + RedisJSON) |
| Inference locale | **Ollama** (Llama 3 + nomic-embed-text)    |
| REST API         | **FastAPI** + uvicorn                      |
| Modelli dati     | **Pydantic v2** + pydantic-settings        |

## Quick start

```bash
# 1. Clona il repository
git clone <repo-url> && cd knowledge-graph-lab

# 2. Configura le variabili d'ambiente
cp .env.example .env
# Modifica NEO4J_PASSWORD in .env

# 3. Avvia l'infrastruttura
docker compose up -d

# 4. Scarica i modelli Ollama
docker compose exec ollama ollama pull llama3
docker compose exec ollama ollama pull nomic-embed-text

# 5. Popola con dati di esempio
make seed
```

## Requisiti

- **Docker 24+** e Docker Compose v2
- **8 GB RAM** raccomandati (Ollama + Neo4j + Redis)
- GPU NVIDIA opzionale (per accelerare Ollama — decommentare sezione `deploy` in `docker-compose.yml`)

## Struttura directory

```
knowledge-graph-lab/
├── config/          # Configurazione centralizzata (pydantic-settings)
├── models/          # Modelli Pydantic (VectorDocument, GraphNode, Relation)
├── pipeline/        # Pipeline di ingestion (chunker, embedder, extractor)
├── storage/         # Backend storage (Neo4j, Redis)
├── query/           # Query pipeline (vector search, graph traversal, RAG)
├── api/             # FastAPI application e routes
├── utils/           # Logger strutturato e helpers
├── tests/           # Test suite con mock
├── scripts/         # Script di seed e demo
├── infra/docker/    # Dockerfile
├── docker-compose.yml
├── requirements.txt
└── Makefile
```

## API Endpoints

| Metodo   | Endpoint          | Descrizione                           |
| -------- | ----------------- | ------------------------------------- |
| `POST`   | `/ingest`         | Carica e indicizza un documento       |
| `POST`   | `/query`          | Query RAG (risposta JSON)             |
| `POST`   | `/query/stream`   | Query RAG con streaming SSE           |
| `GET`    | `/health`         | Health check (Neo4j + Redis + Ollama) |
| `DELETE` | `/documents/{id}` | Cancella un documento                 |

## Variabili d'ambiente

Vedi [`.env.example`](.env.example) per la lista completa delle variabili configurabili.
