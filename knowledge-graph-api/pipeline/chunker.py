"""Text chunking with sentence-aware splitting."""

import re

from config.settings import settings


class TextChunker:
    """Splits text into overlapping chunks respecting sentence boundaries."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def split(self, text: str) -> list[str]:
        """Split *text* into chunks of at most ``chunk_size`` characters.

        Splitting respects sentence boundaries so that sentences are not
        truncated mid-way.  Consecutive chunks share ``chunk_overlap``
        characters of context.

        Args:
            text: The source text to split.

        Returns:
            A list of text chunks.
        """
        if not text or not text.strip():
            return []

        sentences = self._split_sentences(text)
        if not sentences:
            return []

        chunks: list[str] = []
        current_chunk: list[str] = []
        current_length = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # If a single sentence exceeds chunk_size, add it as its own chunk
            if sentence_len > self.chunk_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                chunks.append(sentence)
                continue

            if current_length + sentence_len + (1 if current_chunk else 0) > self.chunk_size:
                # Flush current chunk
                chunks.append(" ".join(current_chunk))

                # Build overlap from the tail of the current chunk
                overlap_chunk: list[str] = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s) + (1 if overlap_chunk else 0) > self.chunk_overlap:
                        break
                    overlap_chunk.insert(0, s)
                    overlap_length += len(s) + (1 if len(overlap_chunk) > 1 else 0)

                current_chunk = overlap_chunk
                current_length = sum(len(s) for s in current_chunk) + max(len(current_chunk) - 1, 0)

            current_chunk.append(sentence)
            current_length += sentence_len + (1 if len(current_chunk) > 1 else 0)

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Naively split text into sentences."""
        raw = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in raw if s.strip()]
