"""Recorded HTTP fixture tests for Google Calendar ingestion (no live network)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import httpx
import pytest

from personal_enigma.domain import PrivateCalendarEvent, PrivatePersonRef
from personal_enigma.ingestion.protocol import SyncCursor
from personal_enigma.ingestion.sources.google_calendar import (
    GoogleCalendarError,
    GoogleCalendarSource,
)

FIXTURES = Path(__file__).parent / "fixtures" / "google_calendar"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _recorded_handler(request: httpx.Request) -> httpx.Response:
    if request.headers.get("Authorization") != "Bearer test-token":
        return httpx.Response(401, json={"error": "unauthorized"})

    path = unquote(request.url.path)
    if path.endswith("/users/me/calendarList"):
        return httpx.Response(200, json=_load("calendar_list.json"))

    if "/calendars/" in path and path.endswith("/events"):
        calendar_id = path.split("/calendars/", 1)[1].rsplit("/events", 1)[0]
        sync_token = request.url.params.get("syncToken")
        if calendar_id == "primary":
            if sync_token == "sync-primary-1":
                return httpx.Response(200, json=_load("events_primary_incremental.json"))
            return httpx.Response(200, json=_load("events_primary.json"))
        if calendar_id == "work@example.com":
            return httpx.Response(200, json=_load("events_work.json"))
        if calendar_id == "holidays":
            return httpx.Response(
                200,
                json={
                    "kind": "calendar#events",
                    "items": [],
                    "nextSyncToken": "sync-holidays-1",
                },
            )
        return httpx.Response(404, json={"error": "not_found", "calendar": calendar_id})

    return httpx.Response(404, json={"error": "not_found", "path": path})


class _RecordingResolver:
    def __init__(self) -> None:
        self.seen: list[str | None] = []

    def resolve_ref(self, ref: PrivatePersonRef) -> str | None:
        self.seen.append(ref.email)
        if ref.email == "alex@example.com":
            return "PERSON_ALEX"
        return None


def _source(**kwargs: Any) -> GoogleCalendarSource:
    defaults: dict[str, Any] = {
        "access_token": "test-token",
        "transport": httpx.MockTransport(_recorded_handler),
        "base_url": "https://www.googleapis.com/calendar/v3",
        "selected_calendar_ids": ["primary"],
        "remote_llm_enabled": False,
    }
    defaults.update(kwargs)
    return GoogleCalendarSource(**defaults)


def test_initial_sync_maps_to_private_calendar_events() -> None:
    async def _run() -> None:
        source = _source(
            contacts_by_email={
                "alex@example.com": PrivatePersonRef(
                    display_name="Alex (Contacts)",
                    email="alex@example.com",
                    provider_id="ab:alex",
                )
            }
        )
        batch = await source.get_changes(None)
        assert batch.exhausted is True
        assert batch.next_cursor is not None
        assert batch.next_cursor.source == "google_calendar"
        assert json.loads(batch.next_cursor.value) == {"primary": "sync-primary-1"}

        events = [PrivateCalendarEvent.model_validate(item) for item in batch.items]
        assert len(events) == 1
        event = events[0]
        assert event.provider == "google_calendar"
        assert event.provider_event_id == "evt_design_review"
        assert event.id == "google_calendar:primary:evt_design_review"
        assert event.calendar_id == "primary"
        assert event.calendar_name == "Personal"
        assert event.title == "Design review"
        assert event.organiser is not None
        assert event.organiser.display_name == "Alex (Contacts)"
        assert event.organiser.provider_id == "ab:alex"
        assert event.attendees[1].email == "sam@example.com"
        assert event.recurrence is not None
        assert event.recurrence.rule == "FREQ=WEEKLY;INTERVAL=1"
        assert event.availability == "busy"

    asyncio.run(_run())


def test_selection_excludes_unchecked_calendars() -> None:
    async def _run() -> None:
        source = _source(selected_calendar_ids=["primary"])
        batch = await source.get_changes(None)
        titles = {item["title"] for item in batch.items}
        assert titles == {"Design review"}
        assert "Work planning" not in titles

        both = _source(selected_calendar_ids=["primary", "work@example.com"])
        both_batch = await both.get_changes(None)
        both_titles = {item["title"] for item in both_batch.items}
        assert both_titles == {"Design review", "Work planning"}
        assert json.loads(both_batch.next_cursor.value) == {
            "primary": "sync-primary-1",
            "work@example.com": "sync-work-1",
        }

    asyncio.run(_run())


def test_empty_selection_does_not_blind_import() -> None:
    async def _run() -> None:
        source = _source(selected_calendar_ids=[])
        batch = await source.get_changes(None)
        assert batch.items == []
        assert batch.exhausted is True

    asyncio.run(_run())


def test_incremental_sync_token_cursor() -> None:
    async def _run() -> None:
        source = _source(selected_calendar_ids=["primary"])
        cursor = SyncCursor(
            value=json.dumps({"primary": "sync-primary-1"}),
            source="google_calendar",
        )
        batch = await source.get_changes(cursor)
        assert len(batch.items) == 1
        event = PrivateCalendarEvent.model_validate(batch.items[0])
        assert event.provider_event_id == "evt_followup"
        assert json.loads(batch.next_cursor.value) == {"primary": "sync-primary-2"}

    asyncio.run(_run())


def test_entity_resolver_invoked_when_available() -> None:
    async def _run() -> None:
        resolver = _RecordingResolver()
        source = _source(entity_resolver=resolver)
        await source.get_changes(None)
        assert "alex@example.com" in resolver.seen
        assert "sam@example.com" in resolver.seen

    asyncio.run(_run())


def test_works_with_remote_llm_disabled() -> None:
    async def _run() -> None:
        source = _source(remote_llm_enabled=False)
        assert source.remote_llm_enabled is False
        batch = await source.get_changes(None)
        assert batch.items

    asyncio.run(_run())


def test_unauthorized_raises() -> None:
    async def _run() -> None:
        source = GoogleCalendarSource(
            access_token="wrong-token",
            selected_calendar_ids=["primary"],
            transport=httpx.MockTransport(_recorded_handler),
        )
        with pytest.raises(GoogleCalendarError, match="rejected access token"):
            await source.get_changes(None)

    asyncio.run(_run())
