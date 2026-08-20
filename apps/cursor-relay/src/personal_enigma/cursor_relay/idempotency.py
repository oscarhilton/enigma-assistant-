"""Correlation / idempotency keys for create paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class IdempotencyError(Exception):
    def __init__(self, message: str, *, code: str = "idempotency_conflict") -> None:
        super().__init__(message)
        self.code = code


@dataclass
class IdempotencyStore:
    """In-memory idempotency map (swap for Redis/SQL in production)."""

    _entries: dict[str, dict[str, Any]] = field(default_factory=dict)

    def _key(self, tool: str, idempotency_key: str) -> str:
        return f"{tool}:{idempotency_key}"

    def get(self, tool: str, idempotency_key: str) -> dict[str, Any] | None:
        return self._entries.get(self._key(tool, idempotency_key))

    def put(self, tool: str, idempotency_key: str, response: dict[str, Any]) -> None:
        self._entries[self._key(tool, idempotency_key)] = response

    def require_key(self, tool: str, idempotency_key: str | None) -> str:
        if not idempotency_key or not str(idempotency_key).strip():
            raise IdempotencyError(
                f"idempotency_key is required for '{tool}'",
                code="idempotency_required",
            )
        return str(idempotency_key).strip()
