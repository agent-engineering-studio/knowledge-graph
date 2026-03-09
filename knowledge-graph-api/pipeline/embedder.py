"""Embedding generation via Ollama HTTP API."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import settings
from utils.logger import logger


class Embedder:
    """Generates embeddings using Ollama's nomic-embed-text model."""

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_EMBEDDING_MODEL

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts sequentially.

        Args:
            texts: Texts to embed.

        Returns:
            List of 768-dimensional vectors.
        """
        vectors: list[list[float]] = []
        for text in texts:
            vec = await self._embed_single(text)
            vectors.append(vec)
        return vectors

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def _embed_single(self, text: str) -> list[float]:
        """Call Ollama embed endpoint for a single text.

        Supports both the current API (POST /api/embed, field "input") and the
        legacy API (POST /api/embeddings, field "prompt") that was removed in
        recent Ollama releases.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try the current Ollama API first (>= 0.1.30)
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": text},
            )
            if response.status_code == 404:
                body = response.json() if response.content else {}
                error_msg = body.get("error", "")
                if "not found" in error_msg.lower() and "model" in error_msg.lower():
                    # Model is not pulled — raise immediately, no point falling back
                    raise RuntimeError(
                        f"Ollama model '{self.model}' not found. "
                        f"Run: ollama pull {self.model}"
                    )
                # Endpoint doesn't exist → fall back to legacy API (Ollama < 0.1.30)
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                response.raise_for_status()
                data = response.json()
                vector: list[float] = data["embedding"]
            else:
                response.raise_for_status()
                data = response.json()
                # New API returns {"embeddings": [[...]], ...}
                vector = data["embeddings"][0]

            logger.debug("embedding_generated", model=self.model, dim=len(vector))
            return vector
