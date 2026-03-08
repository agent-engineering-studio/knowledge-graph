.PHONY: install run test lint build up down up-dev pull-models seed demo neo4j-ui redis-ui \
       mcp-install mcp-test mcp-inspector ui-dev

# ── API ───────────────────────────────────────────────────────────────
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

# ── Docker ────────────────────────────────────────────────────────────
build:
	docker compose build

up:
	docker compose up --build -d

down:
	docker compose down

up-dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

pull-models:
	docker compose exec ollama ollama pull llama3 && docker compose exec ollama ollama pull nomic-embed-text

# ── MCP ───────────────────────────────────────────────────────────────
mcp-install:
	cd knowledge-graph-mcp && pip install -e .

mcp-test:
	cd knowledge-graph-mcp && pytest tests/ -v

mcp-inspector:
	cd knowledge-graph-mcp/src && npx @modelcontextprotocol/inspector python -m kg_mcp.server

# ── UI ────────────────────────────────────────────────────────────────
ui-dev:
	cd knowledge-graph-ui && npm run dev

# ── Utilities ─────────────────────────────────────────────────────────
neo4j-ui:
	python -m webbrowser http://localhost:7474

redis-ui:
	python -m webbrowser http://localhost:8001
