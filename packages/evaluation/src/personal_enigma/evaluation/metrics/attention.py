"""Attention metrics placeholder (D7)."""

from __future__ import annotations


def critical_recall(*, predicted: int, expected: int) -> float:
    """Stub critical-obligation recall."""
    if expected <= 0:
        return 1.0
    return predicted / expected
