"""Tests for shared turn kernel types and fulfilment derivation."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.api.demo_orchestrator import LlmTrace
from personal_enigma.api.demo_tools import ToolExecutionResult
from personal_enigma.api.turn_kernel import (
    ExecutionPlan,
    WorldTurnProfile,
    agent_work_label_from_outcome,
    attach_kernel_forensics,
    derive_turn_outcome,
)

PILOT_NOW = datetime(2026, 8, 18, 10, 0, tzinfo=UTC)


def _write_pilot_fixture(path: Path, reference: datetime) -> None:
    tomorrow = (reference + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    events = [
        {
            "id": "cal-standup-tomorrow",
            "provider": "apple_calendar",
            "provider_event_id": "evt-standup",
            "title": "Team standup",
            "start_at": tomorrow.isoformat(),
            "end_at": (tomorrow + timedelta(minutes=30)).isoformat(),
            "all_day": False,
        }
    ]
    path.write_text(json.dumps({"events": events}), encoding="utf-8")


def _my_enigma_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fixture_path: Path,
) -> TestClient:
    monkeypatch.setenv("ENIGMA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LLM_DISABLED", "1")
    monkeypatch.setenv("ENIGMA_CALENDAR_FIXTURE", str(fixture_path))
    client = TestClient(create_app())
    registry = client.app.state.world_registry  # type: ignore[attr-defined]
    registry.active.clock.now = lambda: PILOT_NOW  # type: ignore[method-assign]
    return client


def _post(client: TestClient, text: str) -> dict:
    response = client.post("/worlds/my_enigma/conversation/message", json={"text": text})
    assert response.status_code == 200
    return response.json()


def _executed_tool(payload: dict) -> tuple[str | None, dict]:
    executed = payload["llm_trace"].get("executed_tool_request") or []
    if not executed:
        return None, {}
    row = executed[0]
    return row.get("name"), row.get("arguments") or {}


@pytest.fixture
def kernel_my_enigma_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    fixture = tmp_path / "calendar.json"
    _write_pilot_fixture(fixture, PILOT_NOW)
    return _my_enigma_client(tmp_path, monkeypatch, fixture_path=fixture)


def test_derive_turn_outcome_fulfilled_when_planned_matches_executed() -> None:
    plan = ExecutionPlan(planned_capabilities=("briefing.read",))
    outcome = derive_turn_outcome(
        planned=plan,
        executed_names=["briefing.read"],
        tool_results=[ToolExecutionResult(name="briefing.read", ok=True, data={}, turn_items=[])],
    )
    assert outcome.status == "fulfilled"
    assert outcome.coverage_adequate is True


def test_derive_turn_outcome_misdispatched() -> None:
    plan = ExecutionPlan(planned_capabilities=("briefing.read",))
    outcome = derive_turn_outcome(
        planned=plan,
        executed_names=["world.explain"],
        tool_results=[],
        misdispatched=True,
    )
    assert outcome.status == "misdispatched"
    assert outcome.coverage_adequate is False


def test_agent_work_label_from_briefing_outcome() -> None:
    plan = ExecutionPlan(planned_capabilities=("briefing.read",))
    outcome = derive_turn_outcome(
        planned=plan,
        executed_names=["briefing.read"],
        tool_results=[ToolExecutionResult(name="briefing.read", ok=True, data={}, turn_items=[])],
    )
    assert agent_work_label_from_outcome(outcome, tool_name="briefing.read") == "Checked your week"


def test_run_alex_turn_intent_path_stamps_outcome_and_forensics() -> None:
    from personal_enigma.api.conversation_context import ConversationContext
    from personal_enigma.api.demo_projection import project_checkpoint
    from personal_enigma.api.turn_kernel import run_alex_turn

    state = project_checkpoint("cp-2026-01-19T10:00").state
    ctx = ConversationContext()
    profile = WorldTurnProfile(
        world_id="alex_lab",
        environment="demo",
        authority_ceiling="FULL",
    )
    result = run_alex_turn(
        text="Hey, how's my week?",
        at=state.simulated_time,
        corr="corr-alex-test",
        profile=profile,
        conversation_context=ctx,
        llm_enabled=False,
        state=state,
        checkpoint_id="cp-2026-01-19T10:00",
        prior_state=None,
        conversation=[],
        completed_item_ids=set(),
    )
    assert result.outcome.status == "fulfilled"
    assert "briefing.read" in result.outcome.planned_capabilities
    assert result.llm_trace.get("forensic_provenance") is not None
    turn_outcome = result.llm_trace.get("turn_outcome")
    assert turn_outcome is not None
    assert turn_outcome.get("agent_work_label") == "Checked your week"


def test_attach_kernel_forensics_populates_provenance() -> None:
    trace = LlmTrace(
        path="intent_router",
        planner="conversation",
        user_message="hello",
        conversation_state={},
        correlation_id="corr-test",
    )
    profile = WorldTurnProfile(
        world_id="my_enigma",
        environment="private",
        authority_ceiling="READ_SUPPORT",
    )
    payload = attach_kernel_forensics(trace, profile=profile)
    assert payload.get("forensic_provenance") is not None
    build = payload["forensic_provenance"]["build"]
    assert build.get("git_sha")


def test_private_elliptical_followups_inherit_intent_and_period(
    kernel_my_enigma_client: TestClient,
) -> None:
    """KERNEL-01: horizon follow-ups compose with last intent — not stale temporal_constraint."""
    _post(kernel_my_enigma_client, "What's on today?")

    tomorrow = _post(kernel_my_enigma_client, "tomorrow?")
    tool, args = _executed_tool(tomorrow)
    assert tool == "availability.check"
    assert args.get("period") == "tomorrow"
    assert "tomorrow" in tomorrow["items"][0]["text"].lower()
    assert "Team standup" in tomorrow["items"][0]["text"]

    next_week = _post(kernel_my_enigma_client, "Next week?")
    tool, args = _executed_tool(next_week)
    assert tool == "availability.check"
    assert args.get("period") == "next_week"

    show_me = _post(kernel_my_enigma_client, "Show me")
    tool, _args = _executed_tool(show_me)
    assert tool == "availability.check"
    assert show_me["llm_trace"]["conversation_state"].get("frame_inherited") is True

    free_now = _post(kernel_my_enigma_client, "im free now?")
    tool, args = _executed_tool(free_now)
    assert tool == "availability.check"
    assert args.get("period") == "today"


def test_private_kernel_interpret_request_path_stamps_capsule(
    kernel_my_enigma_client: TestClient,
) -> None:
    """My Enigma uses interpret_request + capsule — not the removed private router fork."""
    payload = _post(kernel_my_enigma_client, "What's on today?")
    assert payload["llm_trace"]["planner"] == "private_calendar_read"
    ctx = payload["context"]
    assert ctx.get("last_intent") is not None
    assert ctx.get("capsule") is not None
    assert ctx["capsule"]["evidence_domain"] == "PRIVATE_WORLD"


def test_private_phatic_and_gk_never_inherit_calendar_tools(
    kernel_my_enigma_client: TestClient,
) -> None:
    """KERNEL safety: phatic/GK turns do not retrieve after a calendar frame."""
    _post(kernel_my_enigma_client, "What's on today?")

    phatic = _post(kernel_my_enigma_client, "Yep, im so ready for you")
    assert phatic["llm_trace"]["planner"] == "conversation"
    assert phatic["llm_trace"]["conversation_state"].get("semantic_router") is True
    assert _executed_tool(phatic)[0] is None

    gk = _post(kernel_my_enigma_client, "What's the capital of France?")
    assert gk["llm_trace"]["planner"] == "general_knowledge_ejected"
    assert gk["llm_trace"]["conversation_state"].get("evidence_domain") == "GENERAL_KNOWLEDGE"
    assert gk["llm_trace"]["conversation_state"].get("semantic_router") is True
    assert _executed_tool(gk)[0] is None
    assert gk["context"].get("capsule") is None


def test_general_knowledge_routes_via_semantic_router_not_regex(
    kernel_my_enigma_client: TestClient,
) -> None:
    """GK domain is owned by the semantic router merge — not kernel regex heuristics."""
    _post(kernel_my_enigma_client, "What's on today?")
    gk = _post(kernel_my_enigma_client, "What's the capital of France?")
    state = gk["llm_trace"]["conversation_state"]
    assert state.get("semantic_router") is True
    assert state.get("evidence_domain") == "GENERAL_KNOWLEDGE"
    assert gk["llm_trace"]["planner"] == "general_knowledge_ejected"


def test_who_is_phrase_in_calendar_context_not_regex_misrouted(
    kernel_my_enigma_client: TestClient,
) -> None:
    """Overlapping 'who is' phrasing stays private when the router inherits the frame."""
    _post(kernel_my_enigma_client, "What am I doing tomorrow?")
    turn = _post(kernel_my_enigma_client, "Who is she meeting?")
    state = turn["llm_trace"]["conversation_state"]
    assert state.get("semantic_router") is True
    assert state.get("evidence_domain") == "PRIVATE_WORLD"
    assert turn["llm_trace"]["planner"] == "private_calendar_read"


def test_elliptical_show_me_inherits_active_frame_via_router(
    kernel_my_enigma_client: TestClient,
) -> None:
    """Bare 'show me' inherits the active calendar frame through router + compose_intent."""
    _post(kernel_my_enigma_client, "What's on today?")
    turn = _post(kernel_my_enigma_client, "Show me")
    state = turn["llm_trace"]["conversation_state"]
    assert state.get("semantic_router") is True
    assert state.get("frame_inherited") is True
    tool, _args = _executed_tool(turn)
    assert tool == "availability.check"
