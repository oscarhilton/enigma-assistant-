"""Text chunking for the local embed → index pipeline."""

from __future__ import annotations


def chunk_text(text: str, *, max_chars: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping character windows suitable for embedding."""
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be >= 0 and < max_chars")
    if len(cleaned) <= max_chars:
        return [cleaned]

    chunks: list[str] = []
    step = max_chars - overlap
    start = 0
    while start < len(cleaned):
        end = min(start + max_chars, len(cleaned))
        chunks.append(cleaned[start:end])
        if end >= len(cleaned):
            break
        start += step
    return chunks
