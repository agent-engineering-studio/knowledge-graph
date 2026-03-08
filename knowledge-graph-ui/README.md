# knowledge-graph-ui

Web frontend for the **Knowledge Graph Lab** project.
Single-page application built with Next.js 15 (App Router), React 19, Tailwind CSS v4 and an interactive force-directed graph view.

> Full project documentation in the [root README](../README.md).

---

## Table of contents

- [Stack](#stack)
- [Prerequisites](#prerequisites)
- [Local setup](#local-setup)
- [Configuration](#configuration)
- [Running](#running)
- [Pages](#pages)
- [API client](#api-client)
- [Testing and linting](#testing-and-linting)
- [Docker](#docker)
- [Directory structure](#directory-structure)

---

## Stack

| Component | Technology |
| --- | --- |
| Framework | Next.js 15 (App Router) |
| UI library | React 19 |
| Styling | Tailwind CSS v4 |
| Graph visualisation | react-force-graph-2d 1.26+ |
| Icons | lucide-react |
| Language | TypeScript 5.7+ |
| Linting | ESLint 9+ |
| Build | next build (standalone output) |

---

## Prerequisites

- Node.js 22+
- API backend reachable at `http://localhost:8000`

Start the API (from the repo root):

```bash
make up-infra   # infrastructure only (Docker)
make run        # FastAPI with hot-reload
```

---

## Local setup

```bash
cd knowledge-graph-ui

# Install dependencies
npm install

# Configure environment variables
cp .env.local.example .env.local
# Verify: NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Configuration

File `.env.local` (do not commit):

| Variable | Default | Description |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL of the FastAPI backend |
| `NEXT_PUBLIC_ENABLE_STREAMING` | `true` | Enable SSE streaming for queries |
| `NEXT_PUBLIC_ENABLE_GRAPH_VIEW` | `true` | Feature flag for the graph view page |

---

## Running

```bash
npm run dev      # dev server with hot-reload (port 3000)
npm run build    # production build
npm run start    # serve production build
npm run lint     # ESLint
```

UI available at `http://localhost:3000`.

---

## Pages

### Dashboard (`/`)

- Real-time status indicators for Neo4j, Redis and Ollama
- Quick links to functional pages
- Direct links to Swagger UI, Neo4j Browser and RedisInsight

### Search / Query (`/query`)

- Search form with configurable parameters: `thread_id`, `top_k`, `max_hops`
- SSE streaming: tokens appear in real time as the LLM generates
- Structured result view: answer, sources with relevance score, metadata (intent, nodes, edges, time)

### Graph View (`/graph`)

- Query input to explore sections of the knowledge graph
- Interactive force-directed visualisation (react-force-graph-2d)
- Colour-coded nodes by type, edges with arrows and relation labels
- Zoom, pan and drag support

---

## API client

[`src/lib/api-client.ts`](src/lib/api-client.ts) is the single contract between UI and API:

- TypeScript interfaces mirroring the backend Pydantic models
- Typed functions for every endpoint (`getHealth`, `postQuery`, `postIngest`, `deleteDocument`)
- Async generator `streamQuery()` for SSE streaming
- `AbortSignal` support for cancelling in-flight requests

---

## Testing and linting

```bash
cd knowledge-graph-ui

npm run lint     # ESLint across the whole project
npm run build    # verifies TypeScript compiles without errors
```

---

## Docker

Multi-stage Dockerfile: deps → build → standalone runtime.

```bash
# Start via compose (prod profile)
docker compose --profile prod up ui -d

# Rebuild a single service
docker compose up --build ui -d

# Follow logs
docker compose logs -f ui

# Dev with hot-reload (dev profile + overlay)
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile dev up ui
```

---

## Directory structure

```text
knowledge-graph-ui/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout with Navbar
│   │   ├── page.tsx            # Dashboard (health + quick links)
│   │   ├── query/
│   │   │   └── page.tsx        # Search / Query page
│   │   └── graph/
│   │       └── page.tsx        # Graph View page
│   ├── components/
│   │   ├── Navbar.tsx          # Navigation bar
│   │   ├── HealthStatus.tsx    # Service health indicators
│   │   ├── QueryForm.tsx       # RAG search form
│   │   ├── QueryResults.tsx    # Result display
│   │   └── GraphView.tsx       # Interactive graph (react-force-graph-2d)
│   └── lib/
│       └── api-client.ts       # Typed HTTP client
├── public/                     # Static assets
├── Dockerfile                  # Multi-stage build (standalone output)
├── next.config.ts
├── package.json
├── tsconfig.json
├── postcss.config.mjs
└── .env.local.example
```
