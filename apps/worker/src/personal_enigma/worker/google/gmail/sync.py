"""Gmail sync job stub for the worker (ticket M11).

Runs local Gmail ingestion via ``GmailSource``; never requires remote LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor
from personal_enigma.ingestion.sources.gmail import GmailSource


@dataclass(frozen=True, slots=True)
class GmailSyncRequest:
    """Parameters for a single Gmail sync pass."""

    access_token: str
    cursor_value: str | None = None
    remote_llm_enabled: bool = False


@dataclass(frozen=True, slots=True)
class GmailSyncResult:
    """Outcome of a stubbed Gmail sync job."""

    message_count: int
    next_cursor: str | None
    remote_llm_enabled: bool


async def run_gmail_sync(
    request: GmailSyncRequest,
    *,
    source: GmailSource | None = None,
    **source_kwargs: Any,
) -> GmailSyncResult:
    """Execute read-only Gmail ingestion (inject ``source`` in tests)."""
    gmail = source or GmailSource(
        access_token=request.access_token,
        remote_llm_enabled=request.remote_llm_enabled,
        **source_kwargs,
    )
    cursor = (
        SyncCursor(value=request.cursor_value, source="gmail")
        if request.cursor_value
        else None
    )
    batch: ChangeBatch = await gmail.get_changes(cursor)
    next_value = batch.next_cursor.value if batch.next_cursor else None
    return GmailSyncResult(
        message_count=len(batch.items),
        next_cursor=next_value,
        remote_llm_enabled=request.remote_llm_enabled,
    )
