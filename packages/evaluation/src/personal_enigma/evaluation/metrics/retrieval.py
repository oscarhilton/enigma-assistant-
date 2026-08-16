"""Retrieval metrics placeholder (D7)."""

from __future__ import annotations


def recall_at_k(*, hits: int, k: int) -> float:
    """Stub retrieval recall@k."""
    if k <= 0:
        return 0.0
    return hits / k
