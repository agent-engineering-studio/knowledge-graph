"""File-type routing for the ingestion pipeline."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


def resolve_mime_type(file_path: str) -> str:
    """Return the MIME type for a supported file extension.

    Args:
        file_path: Path to the file.

    Returns:
        The corresponding MIME type string.

    Raises:
        ValueError: If the file extension is not supported.
    """
    ext = Path(file_path).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    return SUPPORTED_EXTENSIONS[ext]
