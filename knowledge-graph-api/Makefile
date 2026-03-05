.PHONY: install run test lint build up down pull-models seed demo neo4j-ui redis-ui

install:
	pip install -r requirements.txt

run:
	uvicorn api.main:app --reload

test:
	pytest tests/ -v

lint:
	ruff check .

build:
	docker build -f infra/docker/Dockerfile -t knowledge-graph-lab .

up:
	docker compose up --build -d

down:
	docker compose down

pull-models:
	docker compose exec ollama ollama pull llama3 && docker compose exec ollama ollama pull nomic-embed-text

seed:
	python scripts/seed_data.py

demo:
	python scripts/demo_query.py

neo4j-ui:
	python -m webbrowser http://localhost:7474

redis-ui:
	python -m webbrowser http://localhost:8001
