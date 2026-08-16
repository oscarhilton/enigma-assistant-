"""Tests for Apple Reminders DataSource (M09)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from personal_enigma.domain import PrivateReminder
from personal_enigma.ingestion.bridge_client import AppleBridgeClient, AppleBridgeError
from personal_enigma.ingestion.sources.apple_reminders import (
    EXPLICIT_REMINDER_INTENT_SIGNAL,
    AppleReminderSource,
)


def _reminder_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "apple_reminders:REM-1",
        "provider": "apple_reminders",
        "provider_id": "REM-1",
        "list_id": "list-1",
        "title": "Send deployment notes",
        "notes": None,
        "due_at": "2026-08-17T09:00:00Z",
        "completed_at": None,
        "is_completed": False,
        "priority": 1,
        "created_at": "2026-08-16T12:00:00Z",
        "updated_at": "2026-08-16T13:00:00Z",
    }
    base.update(overrides)
    return base


def _handler(
    *,
    authorised: bool = True,
    items: list[dict[str, Any]] | None = None,
) -> Any:
    reminders = items if items is not None else [_reminder_payload()]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("Authorization") != "Bearer test-token":
            return httpx.Response(401, json={"error": "unauthorized"})
        if request.url.path != "/reminders/changes":
            return httpx.Response(404, json={"error": "not_found"})

        cursor = request.url.params.get("cursor")
        next_cursor = {
            "value": cursor or "2026-08-16T13:00:00Z",
            "source": "apple_reminders",
        }
        return httpx.Response(
            200,
            json={
                "authorised": authorised,
                "items": reminders if authorised else [],
                "next_cursor": next_cursor if authorised else None,
                "exhausted": True,
            },
        )

    return handler


def test_maps_to_private_reminder_with_apple_reminders_provider() -> None:
    async def _run() -> None:
        transport = httpx.MockTransport(_handler())
        client = AppleBridgeClient(token="test-token", transport=transport)
        source = AppleReminderSource(client)
        batch = await source.get_changes(cursor=None)

        assert len(batch.items) == 1
        reminder = PrivateReminder.model_validate(batch.items[0])
        assert reminder.provider == "apple_reminders"
        assert reminder.provider_id == "REM-1"
        assert reminder.is_completed is False
        assert reminder.due_at is not None
        assert batch.next_cursor is not None
        assert batch.next_cursor.source == "apple_reminders"
        assert batch.exhausted is True

    asyncio.run(_run())


def test_mvp_incomplete_with_due_dates_are_ingested() -> None:
    """Bridge MVP defaults: incomplete + due date → PrivateReminder items."""

    async def _run() -> None:
        items = [
            _reminder_payload(provider_id="open", id="apple_reminders:open", is_completed=False),
        ]
        transport = httpx.MockTransport(_handler(items=items))
        source = AppleReminderSource(AppleBridgeClient(token="test-token", transport=transport))
        batch = await source.get_changes(cursor=None)
        assert all(not item["is_completed"] for item in batch.items)
        assert all(item.get("due_at") for item in batch.items)

    asyncio.run(_run())


def test_unauthorised_returns_empty_exhausted_batch() -> None:
    async def _run() -> None:
        transport = httpx.MockTransport(_handler(authorised=False))
        source = AppleReminderSource(AppleBridgeClient(token="test-token", transport=transport))
        batch = await source.get_changes(cursor=None)
        assert batch.items == []
        assert batch.next_cursor is None
        assert batch.exhausted is True

    asyncio.run(_run())


def test_cursor_is_forwarded_to_bridge() -> None:
    async def _run() -> None:
        seen: dict[str, str | None] = {"cursor": None}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["cursor"] = request.url.params.get("cursor")
            return httpx.Response(
                200,
                json={
                    "authorised": True,
                    "items": [],
                    "next_cursor": {"value": "c2", "source": "apple_reminders"},
                    "exhausted": True,
                },
            )

        transport = httpx.MockTransport(handler)
        source = AppleReminderSource(AppleBridgeClient(token="test-token", transport=transport))
        from personal_enigma.ingestion.protocol import SyncCursor

        batch = await source.get_changes(SyncCursor(value="c1", source="apple_reminders"))
        assert seen["cursor"] == "c1"
        assert batch.next_cursor is not None
        assert batch.next_cursor.value == "c2"

    asyncio.run(_run())


def test_explicit_reminders_are_first_class_intent_signals() -> None:
    """Apple Reminders map to EXPLICIT_REMINDER — stronger than email inference."""
    assert EXPLICIT_REMINDER_INTENT_SIGNAL == "explicit_reminder"
    assert AppleReminderSource.intent_signal == "explicit_reminder"
    assert AppleReminderSource.source_name == "apple_reminders"

    reminder = PrivateReminder.model_validate(_reminder_payload())
    assert reminder.provider == "apple_reminders"
    assert reminder.is_completed is False
    assert reminder.due_at is not None
    # Contract: dated incomplete Apple reminders are explicit user intent, not inferred.
    assert reminder.title == "Send deployment notes"


def test_unauthorized_token_raises() -> None:
    async def _run() -> None:
        transport = httpx.MockTransport(_handler())
        source = AppleReminderSource(AppleBridgeClient(token="wrong", transport=transport))
        with pytest.raises(AppleBridgeError, match="rejected bearer token"):
            await source.get_changes(cursor=None)

    asyncio.run(_run())
