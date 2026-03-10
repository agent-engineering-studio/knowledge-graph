"""Ollama client factory for the Microsoft Agent Framework.

Ollama exposes an OpenAI-compatible REST API at /v1, so we use
``OpenAIChatClient`` pointed at the local Ollama instance.

The model is set via the ``OPENAI_CHAT_MODEL_ID`` environment variable
(agent-framework convention) rather than as a constructor argument.
``base_url`` and ``api_key`` are the only constructor params accepted by
the public-preview package.
"""

from __future__ import annotations

import os

from agent_framework.openai import OpenAIChatClient

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_LLM_MODEL: str = os.getenv("OLLAMA_LLM_MODEL", "qwen2.5:7b")


def get_client() -> OpenAIChatClient:
    """Return an OpenAIChatClient targeting the local Ollama instance.

    The model is injected via the ``OPENAI_CHAT_MODEL_ID`` env var, which is
    the convention used by agent-framework (public preview) for OpenAI-compatible
    clients.  We set it programmatically so callers only need OLLAMA_LLM_MODEL.
    """
    # agent-framework reads the model from this env var for OpenAIChatClient
    os.environ.setdefault("OPENAI_CHAT_MODEL_ID", OLLAMA_LLM_MODEL)

    return OpenAIChatClient(
        base_url=f"{OLLAMA_BASE_URL}/v1",
        api_key="ollama",   # Ollama ignores this value but the client requires it
    )
