"""Worker Google Calendar sync stub tests (recorded transport, no live network)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from personal_enigma.ingestion.sources.google_calendar import GoogleCalendarSource
from personal_enigma.worker.google.calendar import (
    GoogleCalendarSyncRequest,
    run_google_calendar_sync,
)

FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "ingestion"
    / "tests"
    / "fixtures"
    / "google_calendar"
)


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/users/me/calendarList"):
        return httpx.Response(200, json=_load("calendar_list.json"))
    if "/calendars/primary/events" in path:
        return httpx.Response(200, json=_load("events_primary.json"))
    if "work%40example.com" in path or "work@example.com" in path:
        return httpx.Response(200, json=_load("events_work.json"))
    return httpx.Response(404, json={"error": "not_found", "path": path})


def test_run_google_calendar_sync_respects_selection() -> None:
    async def _run() -> None:
        source = GoogleCalendarSource(
            access_token="test-token",
            selected_calendar_ids=["primary"],
            transport=httpx.MockTransport(_handler),
            remote_llm_enabled=False,
        )
        result = await run_google_calendar_sync(
            GoogleCalendarSyncRequest(
                access_token="test-token",
                selected_calendar_ids=("primary",),
                remote_llm_enabled=False,
            ),
            source=source,
        )
        assert result.event_count == 1
        assert result.selected_calendar_ids == ("primary",)
        assert result.remote_llm_enabled is False
        assert result.next_cursor is not None

    asyncio.run(_run())


def test_run_google_calendar_sync_empty_selection() -> None:
    async def _run() -> None:
        source = GoogleCalendarSource(
            access_token="test-token",
            selected_calendar_ids=[],
            transport=httpx.MockTransport(_handler),
        )
        result = await run_google_calendar_sync(
            GoogleCalendarSyncRequest(access_token="test-token", selected_calendar_ids=()),
            source=source,
        )
        assert result.event_count == 0

    asyncio.run(_run())
