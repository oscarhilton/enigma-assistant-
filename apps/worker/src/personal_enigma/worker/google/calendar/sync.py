"""Google Calendar sync job stub for the worker (ticket M12).

Runs local Calendar ingestion via ``GoogleCalendarSource``; never requires remote LLM.
Only selected calendars are synced.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor
from personal_enigma.ingestion.sources.google_calendar import GoogleCalendarSource


@dataclass(frozen=True, slots=True)
class GoogleCalendarSyncRequest:
    """Parameters for a single Google Calendar sync pass."""

    access_token: str
    selected_calendar_ids: tuple[str, ...] = ()
    cursor_value: str | None = None
    remote_llm_enabled: bool = False


@dataclass(frozen=True, slots=True)
class GoogleCalendarSyncResult:
    """Outcome of a stubbed Google Calendar sync job."""

    event_count: int
    next_cursor: str | None
    selected_calendar_ids: tuple[str, ...]
    remote_llm_enabled: bool


async def run_google_calendar_sync(
    request: GoogleCalendarSyncRequest,
    *,
    source: GoogleCalendarSource | None = None,
    **source_kwargs: Any,
) -> GoogleCalendarSyncResult:
    """Execute read-only Calendar ingestion (inject ``source`` in tests)."""
    selected: Sequence[str] = request.selected_calendar_ids
    calendar = source or GoogleCalendarSource(
        access_token=request.access_token,
        selected_calendar_ids=selected,
        remote_llm_enabled=request.remote_llm_enabled,
        **source_kwargs,
    )
    cursor = (
        SyncCursor(value=request.cursor_value, source="google_calendar")
        if request.cursor_value
        else None
    )
    batch: ChangeBatch = await calendar.get_changes(cursor)
    next_value = batch.next_cursor.value if batch.next_cursor else None
    return GoogleCalendarSyncResult(
        event_count=len(batch.items),
        next_cursor=next_value,
        selected_calendar_ids=tuple(request.selected_calendar_ids),
        remote_llm_enabled=request.remote_llm_enabled,
    )
