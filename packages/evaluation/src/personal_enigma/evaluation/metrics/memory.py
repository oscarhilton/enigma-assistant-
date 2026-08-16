"""Memory metrics placeholder (D7)."""

from __future__ import annotations


def checkpoint_hit_rate(*, hits: int, total: int) -> float:
    """Stub memory-checkpoint hit rate."""
    if total <= 0:
        return 1.0
    return hits / total
