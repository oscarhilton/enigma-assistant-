"""P03 — Calendar READ + SUPPORT for My Enigma (freeze bar + pilot scripts)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.api.private_tools import PRIVATE_DENIED_TOOL_NAMES

PILOT_NOW = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)  # Tuesday


def _write_pilot_fixture(path: Path, reference: datetime) -> None:
    tomorrow = (reference + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    saturday = reference + timedelta(days=(5 - reference.weekday()) % 7)
    saturday = saturday.replace(hour=11, minute=0, second=0, microsecond=0)
    monday = reference + timedelta(days=(0 - reference.weekday()) % 7)
    if monday.date() <= reference.date():
        monday = monday + timedelta(days=7)
    monday = monday.replace(hour=14, minute=0, second=0, microsecond=0)

    events = [
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
        },
        {
            "id": "cal-brunch-weekend",
            "provider": "apple_calendar",
            "provider_event_id": "evt-brunch",
            "title": "Brunch with friends",
            "start_at": saturday.isoformat(),
            "end_at": (saturday + timedelta(hours=2)).isoformat(),
            "all_day": False,
        },
        {
            "id": "cal-dentist-monday",
            "provider": "google_calendar",
            "provider_event_id": "evt-dentist",
            "title": "Dentist appointment",
            "start_at": monday.isoformat(),
            "end_at": (monday + timedelta(hours=1)).isoformat(),
            "all_day": False,
        },
    ]
    path.write_text(json.dumps({"events": events}, indent=2), encoding="utf-8")


def _client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fixture_path: Path | None = None,
) -> TestClient:
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LLM_DISABLED", "1")
    monkeypatch.delenv("ENIGMA_ENVIRONMENT_MODE", raising=False)
    if fixture_path is not None:
        monkeypatch.setenv("ENIGMA_CALENDAR_FIXTURE", str(fixture_path))
    else:
        monkeypatch.delenv("ENIGMA_CALENDAR_FIXTURE", raising=False)
    return TestClient(create_app())


def _freeze_my_enigma_clock(client: TestClient, when: datetime) -> None:
    registry = client.app.state.world_registry  # type: ignore[attr-defined]
    monkeypatch_now = lambda: when  # noqa: E731
    registry.active.clock.now = monkeypatch_now  # type: ignore[method-assign]


def test_p03_real_calendar_only_in_my_enigma(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    assert client.post("/worlds/switch", json={"world": "alex_lab"}).status_code == 200
    blocked = client.get("/worlds/my_enigma/calendar/provenance")
    assert blocked.status_code == 409


def test_p03_authority_ceiling_denies_calendar_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)
    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "Book lunch on my calendar tomorrow"},
    )
    assert turn.status_code == 200
    blob = turn.json()["items"][0]["text"].lower()
    assert "change calendar" in blob or "can't prepare" in blob
    assert "assist.propose" in PRIVATE_DENIED_TOOL_NAMES


def test_p03_tomorrow_pilot_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
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
    assert "booking confirmed" not in reply.lower()


def test_p03_weekend_pilot_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)
    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What's coming up this weekend?"},
    )
    assert turn.status_code == 200
    reply = turn.json()["items"][0]["text"]
    assert "Brunch with friends" in reply
    assert "Saturday" in reply


def test_p03_monday_availability_pilot_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)
    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "Am I actually free Monday?"},
    )
    assert turn.status_code == 200
    reply = turn.json()["items"][0]["text"]
    assert "Dentist appointment" in reply
    assert "booking confirmed" not in reply.lower()


def test_p03_world_switch_clears_calendar_conversation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)
    sent = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What am I doing tomorrow?"},
    )
    assert sent.status_code == 200
    assert "Team standup" in sent.json()["items"][0]["text"]

    assert client.post("/worlds/switch", json={"world": "alex_lab"}).status_code == 200
    assert client.post("/worlds/switch", json={"world": "my_enigma"}).status_code == 200
    _freeze_my_enigma_clock(client, PILOT_NOW)
    fresh = client.get("/worlds/my_enigma/conversation").json()
    assert fresh["items"] == []


def test_p03_why_shows_reduced_calendar_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)
    client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What am I doing tomorrow?"},
    )
    why = client.get("/worlds/my_enigma/calendar/provenance").json()
    assert "cal-standup-tomorrow" in why["evidence"]
    assert any("read-only" in row.lower() for row in why["inference"])
    blob = json.dumps(why)
    assert "secret@example.com" not in blob
