"""Minimal passage extraction — select before transform for Notes."""

from __future__ import annotations

# Conservative default: one short passage, never a wholesale note body.
DEFAULT_MAX_PASSAGE_CHARS = 280


def extract_minimal_passage(
    body: str,
    *,
    max_chars: int = DEFAULT_MAX_PASSAGE_CHARS,
) -> str:
    """Return a short passage from note body text.

    Prefers the first non-empty paragraph, then hard-truncates. Callers must
    still treat Notes as HIGH privacy — this does not make content remote-safe.
    """
    text = body.strip()
    if not text:
        return ""

    paragraph = next((p.strip() for p in text.split("\n\n") if p.strip()), text)
    if len(paragraph) <= max_chars:
        return paragraph

    clipped = paragraph[:max_chars]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return f"{clipped}…"
