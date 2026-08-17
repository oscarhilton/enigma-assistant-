"""Egress gate errors."""

from __future__ import annotations


class EgressBlockedError(ValueError):
    """Raised when a payload is refused by the audited egress gate."""
