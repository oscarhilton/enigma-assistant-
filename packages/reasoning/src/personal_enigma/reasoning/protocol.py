"""Protocols for pluggable PAYG reasoning."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from personal_enigma.reasoning.logging import UsageRecord
from personal_enigma.reasoning.modes import ReasoningMode
from personal_enigma.transformation import TransformedContext


class ReasoningResult(BaseModel):
    """Outcome of a reasoning call (or dry-run)."""

    text: str
    model: str
    usage: UsageRecord | None = None
    dry_run: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


@runtime_checkable
class PaygTransport(Protocol):
    """Lowest-level network boundary for a PAYG provider.

    Implementations must not be invoked when the client is DISABLED or DRY_RUN.
    """

    def complete(self, *, model: str, prompt: str, context: TransformedContext) -> ReasoningResult:
        """Perform a remote completion. May open a network connection."""
        ...


@runtime_checkable
class PaygReasoningClient(Protocol):
    """Public PAYG client: TransformedContext in, gated remote reasoning out."""

    @property
    def mode(self) -> ReasoningMode:
        ...

    def reason(
        self,
        context: TransformedContext,
        *,
        prompt: str = "",
        model: str = "payg-default",
    ) -> ReasoningResult:
        """Reason over sanitised context only. Refuses when the privacy gate fails."""
        ...
