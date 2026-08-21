"""Tests for shared turn kernel types and fulfilment derivation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from personal_enigma.api.conversation_context import ConversationContext
from personal_enigma.api.demo_orchestrator import LlmTrace
from personal_enigma.api.demo_tools import ToolExecutionResult
from personal_enigma.api.turn_kernel import (
    ExecutionPlan,
    WorldTurnProfile,
    agent_work_label_from_outcome,
    attach_kernel_forensics,
    derive_turn_outcome,
    run_private_turn,
)


class _EmptyCalendarAdapter:
    def list_events(self) -> list[Any]:
        return []


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


def test_run_private_turn_general_knowledge_ejects_calendar_tools() -> None:
    conversation: list[dict[str, Any]] = []
    result = run_private_turn(
        text="What's the capital of France?",
        at="2026-08-18T10:00:00Z",
        adapter=_EmptyCalendarAdapter(),
        conversation=conversation,
        context=ConversationContext(),
    )
    assert result.llm_trace["planner"] == "general_knowledge_ejected"
    assert result.llm_trace["executed_tool_request"] == []
    assert result.outcome.status == "fulfilled"
    assert "search engine" in result.items[0]["text"].lower()


def test_run_private_turn_authority_refusal_before_calendar_read() -> None:
    conversation: list[dict[str, Any]] = []
    result = run_private_turn(
        text="Book lunch on my calendar tomorrow",
        at="2026-08-18T10:00:00Z",
        adapter=_EmptyCalendarAdapter(),
        conversation=conversation,
        context=ConversationContext(),
    )
    assert result.llm_trace["planner"] == "authority_refusal"
    assert result.llm_trace["executed_tool_request"] == []
    assert "can't create or change calendar" in result.items[0]["text"].lower()


def test_run_private_turn_interpret_request_routes_agenda_with_oracle() -> None:
    conversation: list[dict[str, Any]] = []
    result = run_private_turn(
        text="What's on today?",
        at="2026-08-18T10:00:00Z",
        adapter=_EmptyCalendarAdapter(),
        conversation=conversation,
        context=ConversationContext(),
    )
    assert result.llm_trace["planner"] == "private_calendar_read"
    executed = result.llm_trace["executed_tool_request"]
    assert executed and executed[0]["name"] == "briefing.read"
    assert executed[0]["arguments"]["period"] == "today"
    assert "briefing.read" in result.outcome.planned_capabilities
    assert result.outcome.status == "fulfilled"


def test_run_private_turn_get_my_events_uses_briefing_read() -> None:
    conversation: list[dict[str, Any]] = []
    result = run_private_turn(
        text="Get my events",
        at=datetime(2026, 8, 18, 10, 0, tzinfo=UTC).isoformat(),
        adapter=_EmptyCalendarAdapter(),
        conversation=conversation,
        context=ConversationContext(),
    )
    executed = result.llm_trace["executed_tool_request"]
    assert executed == [{"name": "briefing.read", "arguments": {"period": "this_week"}}]
    assert result.outcome.status == "fulfilled"


def test_run_private_turn_phatic_turn_stays_conversation_only() -> None:
    conversation: list[dict[str, Any]] = []
    result = run_private_turn(
        text="Yep, im so ready for you",
        at="2026-08-18T10:00:00Z",
        adapter=_EmptyCalendarAdapter(),
        conversation=conversation,
        context=ConversationContext(),
    )
    assert result.llm_trace["planner"] == "conversation"
    assert result.llm_trace["executed_tool_request"] == []


def test_run_private_turn_next_work_ignores_stale_calendar_period() -> None:
    ctx = ConversationContext(temporal_constraint="next_week")
    conversation: list[dict[str, Any]] = []
    result = run_private_turn(
        text="What should I do next?",
        at="2026-08-18T10:00:00Z",
        adapter=_EmptyCalendarAdapter(),
        conversation=conversation,
        context=ctx,
    )
    executed = result.llm_trace["executed_tool_request"]
    assert executed == [{"name": "attention.get_current", "arguments": {}}]
    assert result.outcome.status == "fulfilled"
    assert result.outcome.planned_capabilities == ("attention.get_current",)


def test_run_private_turn_prepare_speech_act_refuses_without_regex() -> None:
    conversation: list[dict[str, Any]] = []
    result = run_private_turn(
        text="Please prepare something for my meeting",
        at="2026-08-18T10:00:00Z",
        adapter=_EmptyCalendarAdapter(),
        conversation=conversation,
        context=ConversationContext(),
    )
    assert result.llm_trace["planner"] == "authority_refusal"
    assert result.llm_trace["executed_tool_request"] == []
    assert "can't create or change calendar" in result.items[0]["text"].lower()


@pytest.mark.parametrize(
    "text",
    [
        "The path is clear on Monday",
        "Monday looks clear for the meeting",
    ],
)
def test_run_private_turn_generic_clear_does_not_route_availability(text: str) -> None:
    conversation: list[dict[str, Any]] = []
    result = run_private_turn(
        text=text,
        at="2026-08-18T10:00:00Z",
        adapter=_EmptyCalendarAdapter(),
        conversation=conversation,
        context=ConversationContext(),
    )
    executed = result.llm_trace["executed_tool_request"]
    tool_names = [call["name"] for call in executed]
    assert "availability.check" not in tool_names


@pytest.mark.parametrize(
    "text",
    [
        "Am I free Monday?",
        "Is Monday clear?",
        "Is my schedule clear Monday?",
        "Am I clear Monday?",
    ],
)
def test_run_private_turn_scheduling_clear_availability_routes(text: str) -> None:
    conversation: list[dict[str, Any]] = []
    result = run_private_turn(
        text=text,
        at="2026-08-18T10:00:00Z",
        adapter=_EmptyCalendarAdapter(),
        conversation=conversation,
        context=ConversationContext(),
    )
    executed = result.llm_trace["executed_tool_request"]
    assert executed and executed[0]["name"] == "availability.check"
    assert result.outcome.status == "fulfilled"


def test_run_private_turn_single_tool_plan_is_fulfilled_for_next_work() -> None:
    conversation: list[dict[str, Any]] = []
    result = run_private_turn(
        text="What needs my attention?",
        at="2026-08-18T10:00:00Z",
        adapter=_EmptyCalendarAdapter(),
        conversation=conversation,
        context=ConversationContext(),
    )
    assert result.outcome.status == "fulfilled"
    assert result.outcome.coverage_adequate is True
    assert result.outcome.planned_capabilities == result.outcome.executed_capabilities
