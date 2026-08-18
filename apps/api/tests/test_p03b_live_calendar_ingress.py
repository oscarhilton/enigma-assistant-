"""P03b — production calendar path is the private store, not ENIGMA_CALENDAR_FIXTURE."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.api.private_calendar_store import (
    StoreCalendarAdapter,
    calendar_adapter_for_root,
)
from personal_enigma.api.private_tools import PRIVATE_DENIED_TOOL_NAMES

PILOT_NOW = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)  # Tuesday


def _store_events(reference: datetime) -> list[dict[str, object]]:
    tomorrow = (reference + timedelta(days=1)).replace(
        hour=9, minute=0, second=0, microsecond=0
    )
    return [
        {
            "id": "cal-standup-tomorrow",
            "provider": "apple_calendar",
            "provider_event_id": "evt-standup",
            "title": "Team standup",
            "start_at": tomorrow.isoformat(),
            "end_at": (tomorrow + timedelta(minutes=30)).isoformat(),
            "all_day": False,
            "attendees": [{"email": "secret@example.com", "display_name": "Maya"}],
            "description": "Internal planning — must not leak to remote prompts by default",
        }
    ]


def _write_store(root: Path, events: list[dict[str, object]]) -> Path:
    path = root / "calendar" / "events.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"events": events}, indent=2), encoding="utf-8")
    return path


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LLM_DISABLED", "1")
    monkeypatch.delenv("ENIGMA_ENVIRONMENT_MODE", raising=False)
    monkeypatch.delenv("ENIGMA_CALENDAR_FIXTURE", raising=False)
    return TestClient(create_app())


def _private_root(client: TestClient) -> Path:
    worlds = {row["id"]: row for row in client.get("/worlds").json()["worlds"]}
    return Path(worlds["my_enigma"]["storage_root"])


def _freeze_my_enigma_clock(client: TestClient, when: datetime) -> None:
    registry = client.app.state.world_registry  # type: ignore[attr-defined]
    registry.active.clock.now = lambda: when  # type: ignore[method-assign]


def test_p03b_adapter_is_store_when_fixture_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ENIGMA_CALENDAR_FIXTURE", raising=False)
    adapter = calendar_adapter_for_root(tmp_path / "private")
    assert isinstance(adapter, StoreCalendarAdapter)


def test_p03b_production_route_reads_store_without_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    root = _private_root(client)
    store = _write_store(root, _store_events(PILOT_NOW))
    before = store.read_text(encoding="utf-8")
    _freeze_my_enigma_clock(client, PILOT_NOW)

    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What am I doing tomorrow?"},
    )
    assert turn.status_code == 200
    reply = turn.json()["items"][0]["text"]
    assert "Team standup" in reply
    assert "09:00" in reply
    assert "secret@example.com" not in reply
    assert "Internal planning" not in reply
    assert "booking confirmed" not in reply.lower()

    why = client.get("/worlds/my_enigma/calendar/provenance").json()
    blob = json.dumps(why)
    assert "cal-standup-tomorrow" in why["evidence"]
    assert "secret@example.com" not in blob
    assert "Internal planning" not in blob

    # Observation is not memory — asking must not rewrite the store.
    assert store.read_text(encoding="utf-8") == before
    assert "assist.propose" in PRIVATE_DENIED_TOOL_NAMES


def test_p03b_store_change_and_delete_are_reflected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    root = _private_root(client)
    store = _write_store(root, _store_events(PILOT_NOW))
    _freeze_my_enigma_clock(client, PILOT_NOW)

    first = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What am I doing tomorrow?"},
    )
    assert "Team standup" in first.json()["items"][0]["text"]

    changed = _store_events(PILOT_NOW)
    changed[0]["title"] = "Renamed standup"
    store.write_text(json.dumps({"events": changed}, indent=2), encoding="utf-8")
    second = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What am I doing tomorrow?"},
    )
    assert "Renamed standup" in second.json()["items"][0]["text"]
    assert "Team standup" not in second.json()["items"][0]["text"]

    store.unlink()
    third = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What am I doing tomorrow?"},
    )
    assert "don't see anything" in third.json()["items"][0]["text"].lower()


def test_p03b_alex_cannot_see_private_store_calendar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    _write_store(_private_root(client), _store_events(PILOT_NOW))
    assert client.post("/worlds/switch", json={"world": "alex_lab"}).status_code == 200
    blocked = client.get("/worlds/my_enigma/calendar/provenance")
    assert blocked.status_code == 409
    convo = client.get("/demo/conversation")
    assert convo.status_code == 200
    assert "Team standup" not in json.dumps(convo.json())
