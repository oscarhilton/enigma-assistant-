"""Attention engine protocol stubs."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from personal_enigma.attention.kinds import AttentionKind


class AttentionItem(BaseModel):
    title: str
    body: str
    kind: AttentionKind
    score: float = 0.0
    evidence_ids: list[str] = Field(default_factory=list)
    # 1–5 product priority. 0 means "derive from kind" via surface policy.
    priority: int = 0


@runtime_checkable
class AttentionEngine(Protocol):
    def rank(self, items: list[AttentionItem]) -> list[AttentionItem]:
        """Return attention items ordered by what matters most."""
        ...
