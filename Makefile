.PHONY: \
  install run test lint seed demo \
  build \
  up up-prod up-dev \
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
	$(DC) --profile prod build

# ── Docker: production stack ───────────────────────────────────────────────────
# Full stack: neo4j + redis + ollama + api + ui + mcp + agents
up: up-prod

up-prod:
	$(DC) --profile prod up --build -d

# ── Docker: development stack ─────────────────────────────────────────────────
# Infrastructure + dev tools: neo4j + redis + ollama + redisinsight
# Run app services (api, ui, mcp, agents) locally outside Docker.
up-dev:
	$(DC) --profile dev up -d

# Alias kept for backward compatibility
up-infra: up-dev

# ── Docker: stop ──────────────────────────────────────────────────────────────
down:
	$(DC) --profile prod --profile dev down

# ── Ollama models ──────────────────────────────────────────────────────────────
pull-models:
	$(DC) exec ollama ollama pull llama3
	$(DC) exec ollama ollama pull nomic-embed-text

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
