"""DataSource protocol and change-batch types."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class SyncCursor(BaseModel):
    """Opaque sync cursor for incremental change fetches."""

    value: str
    source: str | None = None


class ChangeBatch(BaseModel):
    """Batch of provider-agnostic changes plus the next cursor."""

    items: list[dict[str, Any]] = Field(default_factory=list)
    next_cursor: SyncCursor | None = None
    exhausted: bool = False


@runtime_checkable
class DataSource(Protocol):
    """Every integration implements this — no provider special-cases in core."""

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        """Return a batch of changes since cursor."""
        ...
