"""Local cost / token usage logging hooks."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from personal_enigma.reasoning.modes import ReasoningMode


class UsageRecord(BaseModel):
    """Local record of estimated remote usage (never sent off-box by this package)."""

    model: str
    mode: ReasoningMode
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float | None = None
    dry_run: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


@runtime_checkable
class UsageLogger(Protocol):
    def log_usage(self, record: UsageRecord) -> None:
        """Persist or emit a local usage record."""
        ...


class InMemoryUsageLogger:
    """Test-friendly usage logger that retains records in process memory."""

    def __init__(self) -> None:
        self.records: list[UsageRecord] = []

    def log_usage(self, record: UsageRecord) -> None:
        self.records.append(record)
