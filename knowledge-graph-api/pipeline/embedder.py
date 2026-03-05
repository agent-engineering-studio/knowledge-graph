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
        """Call Ollama embeddings endpoint for a single text."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            logger.debug("embedding_generated", model=self.model, dim=len(data["embedding"]))
            return data["embedding"]
