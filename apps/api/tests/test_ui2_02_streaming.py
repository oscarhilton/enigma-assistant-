"""UI2-02 — My Enigma conversation SSE stream."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app

PILOT_NOW = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)


def _write_pilot_fixture(path: Path, reference: datetime) -> None:
    tomorrow = (reference + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    payload = {
        "events": [
            {
                "id": "cal-standup",
                "provider": "apple_calendar",
                "provider_event_id": "evt-1",
                "title": "Team standup",
                "start_at": tomorrow.isoformat(),
                "end_at": (tomorrow + timedelta(minutes=30)).isoformat(),
                "all_day": False,
            }
        ]
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, fixture_path: Path) -> TestClient:
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LLM_DISABLED", "1")
    monkeypatch.setenv("ENIGMA_CALENDAR_FIXTURE", str(fixture_path))
    monkeypatch.delenv("ENIGMA_ENVIRONMENT_MODE", raising=False)
    return TestClient(create_app())


def _freeze_clock(client: TestClient, when: datetime) -> None:
    client.app.state.world_registry.active.clock.now = lambda: when  # type: ignore[method-assign]


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for block in raw.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        name = "message"
        data: list[str] = []
        for line in block.split("\n"):
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].strip())
        if data:
            out.append((name, json.loads("\n".join(data))))
    return out


def test_stream_agent_work_before_prose(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_clock(client, PILOT_NOW)
    with client.stream(
        "POST",
        "/worlds/my_enigma/conversation/message/stream",
        json={"text": "What's on tomorrow?"},
        headers={"Accept": "text/event-stream"},
    ) as resp:
        body = resp.read().decode("utf-8")
    events = _parse_sse(body)
    names = [n for n, _ in events]
    assert names[0] == "agent_work"
    assert "prose" in names
    assert names[-1] == "turn_complete"
    assert "error" not in names


def test_agent_work_labels_before_prose(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_clock(client, PILOT_NOW)
    with client.stream(
        "POST",
        "/worlds/my_enigma/conversation/message/stream",
        json={"text": "Am I free tomorrow?"},
        headers={"Accept": "text/event-stream"},
    ) as resp:
        body = resp.read().decode("utf-8")
    events = _parse_sse(body)
    prose_i = next(i for i, (n, _) in enumerate(events) if n == "prose")
    work_i = next(
        i
        for i, (n, d) in enumerate(events)
        if n == "agent_work" and d.get("inspect_labels")
    )
    assert work_i < prose_i


def test_non_streaming_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_clock(client, PILOT_NOW)
    r = client.post("/worlds/my_enigma/conversation/message", json={"text": "What's on tomorrow?"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
