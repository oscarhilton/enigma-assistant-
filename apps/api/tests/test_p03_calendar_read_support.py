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


def test_p03_get_my_events_routes_to_agenda_not_world_explain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _client(tmp_path, monkeypatch)
    _freeze_my_enigma_clock(client, PILOT_NOW)
    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "Get my events"},
    )
    assert turn.status_code == 200
    payload = turn.json()
    trace = payload["llm_trace"]
    assert trace["planner"] == "private_calendar_read"
    assert trace["executed_tool_request"] == [
        {"name": "briefing.read", "arguments": {"period": "this_week"}}
    ]
    reply = payload["items"][0]["text"].lower()
    assert "don't see" in reply or "nothing" in reply or "clear" in reply
    assert "can't prepare" not in reply
    assert "can't change" not in reply


# ---------------------------------------------------------------------------
# CALENDAR_GRAVITY regression tests
# ---------------------------------------------------------------------------


def test_gravity_01_greeting_no_private_calendar_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GRAVITY_01: 'hello!' must not route to private_calendar_read."""
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)

    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "hello!"},
    )
    assert turn.status_code == 200
    payload = turn.json()
    trace = payload["llm_trace"]

    # Must NOT be routed via private_calendar_read planner
    assert trace.get("planner") != "private_calendar_read", (
        "GRAVITY_01: greeting routed to private_calendar_read"
    )
    # Must NOT have executed any calendar tools
    executed = trace.get("executed_tool_request") or []
    tool_names = [t["name"] for t in executed]
    assert "agenda.get" not in tool_names, "GRAVITY_01: agenda.get called for greeting"
    assert "availability.check" not in tool_names, (
        "GRAVITY_01: availability.check called for greeting"
    )
    # Must NOT contain capability disclaimer triggered by private world routing
    reply = payload["items"][0]["text"].lower()
    assert "i can read your calendar" not in reply, (
        "GRAVITY_01: capability disclaimer should not appear for greeting"
    )


def test_gravity_02_this_week_overrides_inherited_today(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GRAVITY_02: 'what about this week?' after today-query must use this_week period."""
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)

    # Turn 1: seed temporal context with "today"
    client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What's on today?"},
    )

    # Turn 2: follow-up with explicit this_week
    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What about this week?"},
    )
    assert turn.status_code == 200
    payload = turn.json()
    trace = payload["llm_trace"]

    executed = trace.get("executed_tool_request") or []
    assert executed, "GRAVITY_02: no tool executed"
    period = executed[0]["arguments"].get("period")
    assert period == "this_week", (
        f"GRAVITY_02: expected this_week, got {period!r} — inherited 'today'"
    )


def test_gravity_03_general_knowledge_ejects_calendar_frame(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GRAVITY_03 + PRIVACY_01: 'whats the capital of france?' after calendar turn."""
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)

    # Seed a prior calendar turn
    client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What's on today?"},
    )

    # General knowledge query — must NOT touch private calendar
    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "whats the capital of france?"},
    )
    assert turn.status_code == 200
    payload = turn.json()
    trace = payload["llm_trace"]

    # PRIVACY_01: planner must NOT be private_calendar_read
    assert trace.get("planner") != "private_calendar_read", (
        "PRIVACY_01: capital-of-france routed to private_calendar_read"
    )

    # No calendar tools executed
    executed = trace.get("executed_tool_request") or []
    tool_names = [t["name"] for t in executed]
    assert "agenda.get" not in tool_names, (
        "GRAVITY_03: agenda.get called for capital-of-france"
    )
    assert "availability.check" not in tool_names, (
        "GRAVITY_03: availability.check called for capital-of-france"
    )

    # Must not give a calendar reply
    reply = payload["items"][0]["text"].lower()
    assert "i don't see anything in your calendar" not in reply, (
        "GRAVITY_03: calendar 'nothing today' reply given for capital-of-france"
    )


def test_gravity_04_after_general_knowledge_no_calendar_resurrection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GRAVITY_04: 'and?' after France answer continues from France, not calendar."""
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)

    # Turn 1: calendar seed
    client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What's on today?"},
    )
    # Turn 2: general knowledge (ejects calendar frame)
    client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "whats the capital of france?"},
    )

    # Turn 3: "and?" — must NOT resurrect calendar with old temporal constraint
    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "and?"},
    )
    assert turn.status_code == 200
    payload = turn.json()

    # After a general-knowledge turn, temporal_constraint should be cleared,
    # so a bare "and?" should not trigger calendar lookup.
    reply = payload["items"][0]["text"].lower()
    assert "i don't see anything in your calendar today" not in reply, (
        "GRAVITY_04: calendar 'nothing today' resurrected after general-knowledge turn"
    )


def test_privacy_01_general_knowledge_never_retrieves_private_calendar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PRIVACY_01 freeze-level: general-knowledge query must never call private calendar tools."""
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)

    general_queries = [
        "whats the capital of france?",
        "who is the president of the united states?",
        "what is the population of tokyo?",
    ]

    for query in general_queries:
        # First seed a calendar context to ensure inheritance is possible
        client.post("/worlds/switch", json={"world": "alex_lab"})
        client.post("/worlds/switch", json={"world": "my_enigma"})
        _freeze_my_enigma_clock(client, PILOT_NOW)
        client.post(
            "/worlds/my_enigma/conversation/message",
            json={"text": "What's on today?"},
        )

        turn = client.post(
            "/worlds/my_enigma/conversation/message",
            json={"text": query},
        )
        assert turn.status_code == 200
        trace = turn.json()["llm_trace"]
        assert trace.get("planner") != "private_calendar_read", (
            f"PRIVACY_01: {query!r} routed to private_calendar_read"
        )
        executed = trace.get("executed_tool_request") or []
        calendar_tools = {
            "agenda.get",
            "briefing.read",
            "calendar.agenda.get",
            "availability.check",
            "world.explain",
            "attention.get_current",
        }
        called = {t["name"] for t in executed} & calendar_tools
        assert not called, (
            f"PRIVACY_01: private tools {called} called for general-knowledge query {query!r}"
        )


def test_week_agenda_01_whats_on_this_week(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """WEEK_AGENDA_01: 'whats on this week?' must route to briefing.read with period=this_week."""
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)

    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "whats on this week?"},
    )
    assert turn.status_code == 200
    trace = turn.json()["llm_trace"]

    assert trace.get("planner") == "private_calendar_read", (
        f"WEEK_AGENDA_01: planner was {trace.get('planner')!r}, expected 'private_calendar_read'"
    )

    executed = trace.get("executed_tool_request") or []
    tool_names = [t["name"] for t in executed]
    assert "briefing.read" in tool_names, (
        f"WEEK_AGENDA_01: briefing.read not called; executed={tool_names}"
    )
    assert "world.explain" not in tool_names, (
        "WEEK_AGENDA_01: world.explain was called — query routed to general knowledge"
    )

    period = next(
        (t["arguments"].get("period") for t in executed if t["name"] == "briefing.read"), None
    )
    assert period == "this_week", (
        f"WEEK_AGENDA_01: expected period='this_week', got {period!r}"
    )

    reply = turn.json()["items"][0]["text"].lower()
    assert "don't see anything" in reply or "this week" in reply, (
        f"WEEK_AGENDA_01: unexpected reply: {reply!r}"
    )


# ---------------------------------------------------------------------------
# Semantic inheritance gate regression tests
# ---------------------------------------------------------------------------


def test_gravity_phatic_01_affirmation_after_calendar_no_private_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GRAVITY_PHATIC_01: phatic/affirmational turn after calendar context → CONVERSATION_ONLY."""
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)

    # Seed a calendar turn so temporal_constraint is set.
    client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What's on today?"},
    )

    # Phatic affirmation — no calendar semantics, no missing referent.
    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "Yep, im so ready for you"},
    )
    assert turn.status_code == 200
    payload = turn.json()
    trace = payload["llm_trace"]

    assert trace.get("planner") != "private_calendar_read", (
        "GRAVITY_PHATIC_01: phatic turn routed to private_calendar_read"
    )
    executed = trace.get("executed_tool_request") or []
    tool_names = [t["name"] for t in executed]
    calendar_tools = {"agenda.get", "briefing.read", "calendar.agenda.get", "availability.check", "attention.get_current", "world.explain"}
    assert not ({t["name"] for t in executed} & calendar_tools), (
        "GRAVITY_PHATIC_01: calendar tool called for phatic turn"
    )
    assert "availability.check" not in tool_names, (
        "GRAVITY_PHATIC_01: availability.check called for phatic turn"
    )
    assert "world.explain" not in tool_names, (
        "GRAVITY_PHATIC_01: world.explain called for phatic turn"
    )
    reply = payload["items"][0]["text"].lower()
    assert "calendarNegativeEvidence" not in reply
    assert "i don't see anything in your calendar" not in reply


def test_gravity_general_01_gk_after_calendar_no_calendar_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GRAVITY_GENERAL_01: GK query after calendar context → no calendar tool."""
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)

    client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What's on today?"},
    )

    turn = client.post(
        "/worlds/my_enigma/conversation/message",
        json={"text": "What's the capital of France?"},
    )
    assert turn.status_code == 200
    trace = turn.json()["llm_trace"]
    assert trace.get("planner") != "private_calendar_read", (
        "GRAVITY_GENERAL_01: GK routed to private_calendar_read"
    )
    executed = trace.get("executed_tool_request") or []
    tool_names = [t["name"] for t in executed]
    assert "agenda.get" not in tool_names
    assert "availability.check" not in tool_names


def test_private_context_selection_01_conversational_no_private_retrieval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PRIVATE_CONTEXT_SELECTION_01 (freeze invariant): inherited calendar frame must NOT
    cause private retrieval when the current turn is CONVERSATIONAL."""
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    client = _client(tmp_path, monkeypatch, fixture_path=fixture)
    _freeze_my_enigma_clock(client, PILOT_NOW)

    conversational_turns = [
        "Yep, im so ready for you",
        "sounds good",
        "ok!",
        "thanks",
        "let's go",
        "i'm here",
    ]

    for phrase in conversational_turns:
        # Re-seed calendar context for each phrase.
        client.post("/worlds/switch", json={"world": "alex_lab"})
        client.post("/worlds/switch", json={"world": "my_enigma"})
        _freeze_my_enigma_clock(client, PILOT_NOW)
        client.post(
            "/worlds/my_enigma/conversation/message",
            json={"text": "What's on today?"},
        )

        turn = client.post(
            "/worlds/my_enigma/conversation/message",
            json={"text": phrase},
        )
        assert turn.status_code == 200, f"PRIVATE_CONTEXT_SELECTION_01: HTTP error for {phrase!r}"
        trace = turn.json()["llm_trace"]
        assert trace.get("planner") != "private_calendar_read", (
            f"PRIVATE_CONTEXT_SELECTION_01: {phrase!r} routed to private_calendar_read"
        )
        executed = trace.get("executed_tool_request") or []
        private_tools = {
            "agenda.get",
            "availability.check",
            "world.explain",
            "attention.get_current",
        }
        called = {t["name"] for t in executed} & private_tools
        assert not called, (
            f"PRIVATE_CONTEXT_SELECTION_01: private tools {called} "
            f"called for conversational {phrase!r}"
        )
