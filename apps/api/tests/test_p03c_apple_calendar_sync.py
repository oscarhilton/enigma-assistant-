"""P03c — operator-triggered Apple calendar sync into My Enigma private store."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.api.private_calendar_sync import (
    fetch_apple_calendar_events,
    pilot_calendar_ids_for_root,
    sync_apple_calendar_to_store,
)
from personal_enigma.api.private_tools import (
    PRIVATE_ALLOWED_TOOL_NAMES,
    PRIVATE_DENIED_TOOL_NAMES,
)
from personal_enigma.ingestion.bridge_client import AppleBridgeClient

PILOT_NOW = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)

BRIDGE_EVENT = {
    "id": "apple_calendar:EK-goose",
    "provider": "apple_calendar",
    "provider_event_id": "EK-goose",
    "calendar_id": "cal-pilot",
    "calendar_name": "Pilot",
    "title": "Goose Calibration",
    "description": "Secret description — must stay in store only",
    "start_at": (PILOT_NOW + timedelta(days=1)).replace(hour=14, minute=30).isoformat(),
    "end_at": (PILOT_NOW + timedelta(days=1)).replace(hour=15, minute=0).isoformat(),
    "all_day": False,
    "attendees": [{"email": "hidden@example.com", "display_name": "Hidden"}],
}


def _bridge_handler(request: httpx.Request) -> httpx.Response:
    if request.headers.get("Authorization") != "Bearer pilot-token":
        return httpx.Response(401, json={"error": "unauthorized"})
    if request.url.path != "/calendar/changes":
        return httpx.Response(404, json={"error": "not_found"})
    return httpx.Response(
        200,
        json={
            "authorised": True,
            "items": [BRIDGE_EVENT],
            "next_cursor": None,
            "exhausted": True,
        },
    )


def _mock_bridge_client() -> AppleBridgeClient:
    return AppleBridgeClient(
        token="pilot-token",
        transport=httpx.MockTransport(_bridge_handler),
    )


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LLM_DISABLED", "1")
    monkeypatch.setenv("ENIGMA_BRIDGE_TOKEN", "pilot-token")
    monkeypatch.setenv("ENIGMA_PILOT_APPLE_CALENDAR_IDS", "cal-pilot")
    monkeypatch.delenv("ENIGMA_CALENDAR_FIXTURE", raising=False)
    monkeypatch.setattr(
        "personal_enigma.api.private_calendar_sync.bridge_client_from_env",
        _mock_bridge_client,
    )
    return TestClient(create_app())


def _private_root(client: TestClient) -> Path:
    worlds = {row["id"]: row for row in client.get("/worlds").json()["worlds"]}
    return Path(worlds["my_enigma"]["storage_root"])


def _freeze_my_enigma_clock(client: TestClient, when: datetime) -> None:
    registry = client.app.state.world_registry  # type: ignore[attr-defined]
    registry.active.clock.now = lambda: when  # type: ignore[method-assign]


def test_p03c_pilot_calendar_ids_from_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ENIGMA_PILOT_APPLE_CALENDAR_IDS", "a,b, c")
    assert pilot_calendar_ids_for_root(tmp_path) == ("a", "b", "c")


def test_p03c_pilot_calendar_ids_from_private_config(tmp_path: Path) -> None:
    config = tmp_path / "calendar" / "pilot_selection.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"calendar_ids": ["cal-from-file"]}), encoding="utf-8")
    assert pilot_calendar_ids_for_root(tmp_path) == ("cal-from-file",)


def test_p03c_fetch_maps_bridge_events_to_domain() -> None:
    async def _run() -> None:
        client = _mock_bridge_client()
        events = await fetch_apple_calendar_events(client, ["cal-pilot"])
        assert len(events) == 1
        assert events[0].title == "Goose Calibration"
        assert events[0].attendees[0].email == "hidden@example.com"

    asyncio.run(_run())


def test_p03c_sync_writes_private_store_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ENIGMA_BRIDGE_TOKEN", "pilot-token")
    monkeypatch.setenv("ENIGMA_PILOT_APPLE_CALENDAR_IDS", "cal-pilot")
    monkeypatch.setattr(
        "personal_enigma.api.private_calendar_sync.bridge_client_from_env",
        _mock_bridge_client,
    )

    async def _run() -> None:
        root = tmp_path / "private"
        result = await sync_apple_calendar_to_store(root)
        assert result.event_count == 1
        store_path = root / "calendar" / "events.json"
        assert store_path.exists()
        payload = json.loads(store_path.read_text(encoding="utf-8"))
        assert payload["events"][0]["title"] == "Goose Calibration"

    asyncio.run(_run())


def test_p03c_sync_route_requires_my_enigma(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    sync = client.post("/worlds/my_enigma/calendar/sync")
    assert sync.status_code == 200
    assert sync.json()["event_count"] == 1

    client.post("/worlds/switch", json={"world": "alex_lab"})
    blocked = client.post("/worlds/my_enigma/calendar/sync")
    assert blocked.status_code == 409


def test_p03c_conversation_after_sync_uses_store_without_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    _freeze_my_enigma_clock(client, PILOT_NOW)
    sync = client.post("/worlds/my_enigma/calendar/sync")
    assert sync.status_code == 200

    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What am I doing tomorrow?"},
    )
    assert turn.status_code == 200
    reply = turn.json()["items"][0]["text"]
    assert "Goose Calibration" in reply
    assert "14:30" in reply or "2:30" in reply
    assert "hidden@example.com" not in reply
    assert "Secret description" not in reply


def test_p03c_sync_not_assistant_tool() -> None:
    assert "calendar.sync" not in PRIVATE_ALLOWED_TOOL_NAMES
    assert "calendar.sync" in PRIVATE_DENIED_TOOL_NAMES


def test_p03c_alex_cannot_see_synced_private_calendar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/worlds/my_enigma/calendar/sync")
    client.post("/worlds/switch", json={"world": "alex_lab"})
    blocked = client.get("/worlds/my_enigma/calendar/provenance")
    assert blocked.status_code == 409
    demo = client.get("/demo/conversation")
    assert "Goose Calibration" not in json.dumps(demo.json())
