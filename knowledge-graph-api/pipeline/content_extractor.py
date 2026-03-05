"""Content extraction from various file formats (PDF, DOCX, TXT)."""

from __future__ import annotations

from pathlib import Path

from utils.logger import logger


class ContentExtractor:
    """Extracts raw text from PDF, DOCX, and TXT files."""

    async def extract(self, file_path: str) -> tuple[str, int]:
        """Extract text content from a file.

        Args:
            file_path: Path to the source file.

        Returns:
            Tuple of (extracted_text, total_pages).
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(path)
        elif suffix == ".docx":
            return self._extract_docx(path)
        elif suffix == ".txt":
            return self._extract_txt(path)
        else:
            logger.warning("unsupported_file_type", suffix=suffix, path=str(path))
            raise ValueError(f"Unsupported file type: {suffix}")

    @staticmethod
    def _extract_pdf(path: Path) -> tuple[str, int]:
        """Extract text from a PDF file using pypdf."""
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages_text: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages_text.append(text)
        return "\n\n".join(pages_text), len(reader.pages)

    @staticmethod
    def _extract_docx(path: Path) -> tuple[str, int]:
        """Extract text from a DOCX file using python-docx."""
        from docx import Document

        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs), 1

    @staticmethod
    def _extract_txt(path: Path) -> tuple[str, int]:
        """Read a plain text file."""
        text = path.read_text(encoding="utf-8")
        return text, 1
