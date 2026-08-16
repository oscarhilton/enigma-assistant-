"""Tests for Apple Notes DataSource (M13)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from personal_enigma.domain import PrivateNote
from personal_enigma.ingestion.bridge_client import AppleBridgeClient, AppleBridgeError
from personal_enigma.ingestion.sources.apple_notes import (
    NOTES_CAPABILITY_QUALITY,
    AppleNotesSource,
)


def _note_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "apple_notes:NOTE-1",
        "provider": "apple_notes",
        "provider_note_id": "NOTE-1",
        "folder": "Inbox",
        "title": "Local ideas",
        "body_text": "Keep this wholesale body on-device only.",
        "created_at": "2026-08-16T12:00:00Z",
        "updated_at": "2026-08-16T13:00:00Z",
        "metadata": {
            "quality": "best_effort",
            "access": "apple_events",
            "wholesale_body_remote_safe": "false",
            "remote_privacy_default": "high",
        },
    }
    base.update(overrides)
    return base


def _handler(
    *,
    authorised: bool = True,
    items: list[dict[str, Any]] | None = None,
) -> Any:
    notes = items if items is not None else [_note_payload()]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("Authorization") != "Bearer test-token":
            return httpx.Response(401, json={"error": "unauthorized"})
        if request.url.path != "/notes/changes":
            return httpx.Response(404, json={"error": "not_found"})

        cursor = request.url.params.get("cursor")
        next_cursor = {
            "value": cursor or "2026-08-16T13:00:00Z|NOTE-1",
            "source": "apple_notes",
        }
        return httpx.Response(
            200,
            json={
                "authorised": authorised,
                "items": notes if authorised else [],
                "next_cursor": next_cursor if authorised else None,
                "exhausted": True,
            },
        )

    return handler


def test_maps_to_private_note_with_apple_notes_provider() -> None:
    async def _run() -> None:
        transport = httpx.MockTransport(_handler())
        client = AppleBridgeClient(token="test-token", transport=transport)
        source = AppleNotesSource(client)
        batch = await source.get_changes(cursor=None)

        assert len(batch.items) == 1
        note = PrivateNote.model_validate(batch.items[0])
        assert note.provider == "apple_notes"
        assert note.provider_note_id == "NOTE-1"
        assert note.body_text == "Keep this wholesale body on-device only."
        assert note.metadata["wholesale_body_remote_safe"] == "false"
        assert note.metadata["remote_privacy_default"] == "high"
        assert batch.next_cursor is not None
        assert batch.next_cursor.source == "apple_notes"
        assert batch.exhausted is True

    asyncio.run(_run())


def test_unauthorised_returns_empty_exhausted_batch() -> None:
    async def _run() -> None:
        transport = httpx.MockTransport(_handler(authorised=False))
        source = AppleNotesSource(AppleBridgeClient(token="test-token", transport=transport))
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
                    "next_cursor": {"value": "c2", "source": "apple_notes"},
                    "exhausted": True,
                },
            )

        transport = httpx.MockTransport(handler)
        source = AppleNotesSource(AppleBridgeClient(token="test-token", transport=transport))
        from personal_enigma.ingestion.protocol import SyncCursor

        batch = await source.get_changes(SyncCursor(value="c1", source="apple_notes"))
        assert seen["cursor"] == "c1"
        assert batch.next_cursor is not None
        assert batch.next_cursor.value == "c2"

    asyncio.run(_run())


def test_capability_quality_is_best_effort() -> None:
    assert NOTES_CAPABILITY_QUALITY == "best_effort"
    assert AppleNotesSource.capability_quality == "best_effort"
    assert AppleNotesSource.source_name == "apple_notes"


def test_unauthorized_token_raises() -> None:
    async def _run() -> None:
        transport = httpx.MockTransport(_handler())
        source = AppleNotesSource(AppleBridgeClient(token="wrong", transport=transport))
        with pytest.raises(AppleBridgeError, match="rejected bearer token"):
            await source.get_changes(cursor=None)

    asyncio.run(_run())
