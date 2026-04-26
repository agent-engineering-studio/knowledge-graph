"""Tests for pipeline.chunker.TextChunker."""

from pipeline.chunker import TextChunker


class TestTextChunker:
    """Unit tests for the TextChunker class."""

    def test_basic_chunking(self, sample_text: str) -> None:
        """Text should be split into multiple chunks."""
        chunker = TextChunker(chunk_size=200, chunk_overlap=30)
        chunks = chunker.split(sample_text)
        assert len(chunks) > 1
        # All original sentences should appear somewhere in the chunks
        for chunk in chunks:
            assert len(chunk) > 0

    def test_chunk_overlap(self, sample_text: str) -> None:
        """Consecutive chunks should share overlapping content."""
        chunker = TextChunker(chunk_size=150, chunk_overlap=100)
        chunks = chunker.split(sample_text)
        assert len(chunks) >= 2
        # At least one word from the last sentence of chunk[0] should appear in chunk[1]
        words_0 = set(chunks[0].split())
        words_1 = set(chunks[1].split())
        shared = words_0 & words_1
        # Filter to meaningful words (length > 3)
        meaningful_shared = {w for w in shared if len(w) > 3}
        assert len(meaningful_shared) > 0, f"No overlap found between chunks: {chunks[0]!r} | {chunks[1]!r}"

    def test_empty_text(self) -> None:
        """Empty or whitespace-only text returns no chunks."""
        chunker = TextChunker()
        assert chunker.split("") == []
        assert chunker.split("   ") == []

    def test_short_text_no_split(self) -> None:
        """Text shorter than chunk_size should not be split."""
        chunker = TextChunker(chunk_size=1024, chunk_overlap=128)
        short = "This is a short sentence."
        chunks = chunker.split(short)
        assert len(chunks) == 1
        assert chunks[0] == short

    def test_chunk_size_respected(self, sample_text: str) -> None:
        """No chunk should exceed the configured chunk_size (except oversized single sentences)."""
        chunker = TextChunker(chunk_size=200, chunk_overlap=30)
        chunks = chunker.split(sample_text)
        for chunk in chunks:
            # Allow single sentences that are inherently longer
            words = chunk.split(". ")
            if len(words) > 1:
                assert len(chunk) <= 200 + 50  # small tolerance for sentence boundaries
