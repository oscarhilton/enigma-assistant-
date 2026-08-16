"""Privacy metrics — including adversarial zero-leak helpers (D09)."""

from __future__ import annotations

from collections.abc import Sequence


def direct_identifier_leaks(*, count: int) -> int:
    """Stub count of known direct-identifier leaks (must stay 0)."""
    return count


def count_forbidden_token_leaks(blob: str, forbidden_tokens: Sequence[str]) -> int:
    """Count how many known attack tokens appear in a remote payload blob."""
    return sum(1 for token in forbidden_tokens if token and token in blob)


def zero_leak(*, leak_count: int) -> bool:
    """True when the adversarial / privacy scan found no leaks."""
    return leak_count == 0
