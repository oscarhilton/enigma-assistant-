from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from personal_enigma.ingestion.bridge_client import AppleBridgeClient, AppleBridgeError
from personal_enigma.ingestion.protocol import SyncCursor
from personal_enigma.ingestion.sources.apple_calendar import AppleCalendarSource

SAMPLE_EVENT = {
    "id": "apple_calendar:EK-1",
    "provider": "apple_calendar",
    "provider_event_id": "EK-1",
    "calendar_id": "cal-personal",
    "calendar_name": "Personal",
    "title": "Design review",
    "description": "Bring notes",
    "location": "Room A",
    "url": "https://example.com/meet",
    "start_at": datetime(2026, 8, 16, 14, 0, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
    "end_at": datetime(2026, 8, 16, 15, 0, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
    "all_day": False,
    "availability": "busy",
    "organiser": {
        "display_name": "Alex",
        "email": "alex@example.com",
        "provider_id": "mailto:alex@example.com",
    },
    "attendees": [{"display_name": "Sam", "email": "sam@example.com", "provider_id": None}],
    "recurrence": {"rule": "FREQ=WEEKLY;INTERVAL=1", "raw": {"frequency": "weekly"}},
    "updated_at": datetime(2026, 8, 15, 12, 0, tzinfo=UTC).isoformat().replace("+00:00", "Z"),
}


def _handler(request: httpx.Request) -> httpx.Response:
    if request.headers.get("Authorization") != "Bearer test-token":
        return httpx.Response(401, json={"error": "unauthorized"})
    if request.url.path != "/calendar/changes":
        return httpx.Response(404, json={"error": "not_found"})

    calendars = request.url.params.get("calendar_ids", "")
    if calendars == "denied":
        return httpx.Response(
            200,
            json={"authorised": False, "items": [], "next_cursor": None, "exhausted": True},
        )

    return httpx.Response(
        200,
        json={
            "authorised": True,
            "items": [SAMPLE_EVENT],
            "next_cursor": {"value": "2026-08-15T12:00:00Z", "source": "apple_calendar"},
            "exhausted": True,
        },
    )


def test_get_changes_maps_private_calendar_event() -> None:
    async def _run() -> None:
        client = AppleBridgeClient(
            token="test-token",
            transport=httpx.MockTransport(_handler),
        )
        source = AppleCalendarSource(client, selected_calendar_ids=["cal-personal"])
        batch = await source.get_changes(cursor=SyncCursor(value="2026-01-01T00:00:00Z"))
        assert batch.exhausted is True
        assert batch.next_cursor is not None
        assert batch.next_cursor.source == "apple_calendar"
        assert len(batch.items) == 1
        item = batch.items[0]
        assert item["provider"] == "apple_calendar"
        assert item["calendar_name"] == "Personal"
        assert item["availability"] == "busy"
        assert item["organiser"]["email"] == "alex@example.com"
        assert item["attendees"][0]["display_name"] == "Sam"
        assert item["recurrence"]["rule"] == "FREQ=WEEKLY;INTERVAL=1"

    asyncio.run(_run())


def test_permission_denied_returns_empty_batch() -> None:
    async def _run() -> None:
        client = AppleBridgeClient(
            token="test-token",
            transport=httpx.MockTransport(_handler),
        )
        source = AppleCalendarSource(client, selected_calendar_ids=["denied"])
        batch = await source.get_changes(cursor=None)
        assert batch.items == []
        assert batch.next_cursor is None
        assert batch.exhausted is True

    asyncio.run(_run())


def test_unauthorized_token_raises() -> None:
    async def _run() -> None:
        client = AppleBridgeClient(
            token="wrong-token",
            transport=httpx.MockTransport(_handler),
        )
        source = AppleCalendarSource(client, selected_calendar_ids=["cal-personal"])
        with pytest.raises(AppleBridgeError, match="rejected bearer token"):
            await source.get_changes(cursor=None)

    asyncio.run(_run())
