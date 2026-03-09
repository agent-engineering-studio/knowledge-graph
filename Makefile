.PHONY: \
  install run test lint seed demo \
  build \
  up up-prod up-prod-gpu up-prod-cpu up-dev up-dev-gpu up-dev-cpu \
  down \
  pull-models \
  mcp-install mcp-test mcp-inspector \
  agents-install agents-run agents-test agents-lint \
  ui-dev \
  neo4j-ui redis-ui redisinsight-ui

DC = docker compose

# ── API ────────────────────────────────────────────────────────────────────────
install:
	cd knowledge-graph-api && pip install -r requirements.txt

run:
	cd knowledge-graph-api && uvicorn api.main:app --reload --port 8000

test:
	cd knowledge-graph-api && pytest tests/ -v

lint:
	cd knowledge-graph-api && ruff check .

seed:
	cd knowledge-graph-api && python scripts/seed_data.py

demo:
	cd knowledge-graph-api && python scripts/demo_query.py

# ── Docker: build ──────────────────────────────────────────────────────────────
build:
	$(DC) --profile prod --profile gpu --profile cpu build

build-ollama:
	$(DC) --profile cpu build ollama-cpu

# ── Docker: production stack ───────────────────────────────────────────────────
# Ollama is expected to run on the host (port 11434) by default.
# The api/agents containers reach it via host.docker.internal:11434.
up: up-prod

up-prod:
	$(DC) --profile prod up --build -d

# Full stack + Ollama in Docker with NVIDIA GPU
up-prod-gpu:
	$(DC) --profile prod --profile gpu up --build -d

# Full stack + Ollama in Docker, CPU only (no GPU required)
up-prod-cpu:
	$(DC) --profile prod --profile cpu up --build -d

# ── Docker: development stack ─────────────────────────────────────────────────
# Infrastructure only: neo4j + redis + redisinsight (Ollama on host).
up-dev:
	$(DC) --profile dev up -d

# Infra + Ollama in Docker with NVIDIA GPU
up-dev-gpu:
	$(DC) --profile dev --profile gpu up -d

# Infra + Ollama in Docker, CPU only (no GPU required)
up-dev-cpu:
	$(DC) --profile dev --profile cpu up -d

# Alias kept for backward compatibility
up-infra: up-dev

# ── Docker: stop ──────────────────────────────────────────────────────────────
down:
	$(DC) --profile prod --profile dev --profile gpu --profile cpu down

# ── Ollama models ──────────────────────────────────────────────────────────────
# Models are pulled automatically at container startup via the entrypoint script.
# Use these targets to force a re-pull (e.g. to update to a newer version).
pull-models-gpu:
	$(DC) --profile gpu exec ollama-gpu ollama pull nomic-embed-text
	$(DC) --profile gpu exec ollama-gpu ollama pull llama3

pull-models-cpu:
	$(DC) --profile cpu exec ollama-cpu ollama pull nomic-embed-text
	$(DC) --profile cpu exec ollama-cpu ollama pull llama3

# Force re-pull on the host Ollama (no Docker profile needed)
pull-models:
	ollama pull nomic-embed-text
	ollama pull llama3

# ── MCP ───────────────────────────────────────────────────────────────────────
mcp-install:
	cd knowledge-graph-mcp && pip install -e .

mcp-test:
	cd knowledge-graph-mcp && pytest tests/ -v

mcp-inspector:
	cd knowledge-graph-mcp/src && npx @modelcontextprotocol/inspector python -m kg_mcp.server

# ── Agents ────────────────────────────────────────────────────────────────────
agents-install:
	cd knowledge-graph-agents && pip install -r requirements.txt

agents-run:
	cd knowledge-graph-agents && uvicorn api.agent_api:app --reload --port 8001

agents-test:
	cd knowledge-graph-agents && pytest tests/ -v

agents-lint:
	cd knowledge-graph-agents && ruff check .

# ── UI ────────────────────────────────────────────────────────────────────────
ui-dev:
	cd knowledge-graph-ui && npm run dev

# ── Utilities: open UI in browser ─────────────────────────────────────────────
neo4j-ui:
	python -m webbrowser http://localhost:7474

redis-ui:
	python -m webbrowser http://localhost:8001

redisinsight-ui:
	python -m webbrowser http://localhost:5540
