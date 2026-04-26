"""Pytest configuration for knowledge-graph-agents tests."""

import os

# Set default env vars so imports don't fail without a .env file
os.environ.setdefault("KG_API_URL", "http://localhost:8000")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("OLLAMA_LLM_MODEL", "llama3")
