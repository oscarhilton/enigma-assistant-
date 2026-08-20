"""PRIVACY-01 + CALENDAR_GRAVITY six-turn integration gate via shared kernel."""

from __future__ import annotations

from pathlib import Path

import pytest

from test_p03_calendar_read_support import (
    PILOT_NOW,
    _client,
    _freeze_my_enigma_clock,
    _write_pilot_fixture,
)

CALENDAR_TOOLS = {
    "agenda.get",
    "briefing.read",
    "calendar.agenda.get",
    "availability.check",
    "world.explain",
    "attention.get_current",
}


@pytest.fixture
def gravity_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)
    return client


def _post(client, text: str) -> dict:
    response = client.post("/worlds/my_enigma/conversation/message", json={"text": text})
    assert response.status_code == 200
    return response.json()


def _tool_names(payload: dict) -> set[str]:
    executed = payload["llm_trace"].get("executed_tool_request") or []
    return {row["name"] for row in executed}


def test_gravity_six_turn_sequence(gravity_client) -> None:
    """Six-turn gate: phatic/GK never retrieve; calendar follow-ups bind period."""
    # 1 hello
    hello = _post(gravity_client, "hello!")
    assert hello["llm_trace"]["planner"] == "conversation"
    assert not _tool_names(hello) & CALENDAR_TOOLS

    # 2 today
    today = _post(gravity_client, "What's on today?")
    assert today["llm_trace"]["planner"] == "private_calendar_read"
    assert "briefing.read" in _tool_names(today) or "availability.check" in _tool_names(today)

    # 3 this week
    week = _post(gravity_client, "What about this week?")
    executed = week["llm_trace"]["executed_tool_request"] or []
    briefing = next((t for t in executed if t["name"] == "briefing.read"), None)
    assert briefing is not None
    assert briefing["arguments"].get("period") == "this_week"

    # 4 France
    france = _post(gravity_client, "What's the capital of France?")
    assert france["llm_trace"]["planner"] == "general_knowledge_ejected"
    assert not _tool_names(france) & CALENDAR_TOOLS

    # 5 phatic
    phatic = _post(gravity_client, "Yep, im so ready for you")
    assert phatic["llm_trace"]["planner"] == "conversation"
    assert not _tool_names(phatic) & CALENDAR_TOOLS

    # 6 get events
    events = _post(gravity_client, "Get my events")
    assert "briefing.read" in _tool_names(events)
