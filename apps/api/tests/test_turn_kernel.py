"""Tests for shared turn kernel types and fulfilment derivation."""

from __future__ import annotations

from personal_enigma.api.demo_tools import ToolExecutionResult
from personal_enigma.api.turn_kernel import (
    ExecutionPlan,
    WorldTurnProfile,
    agent_work_label_from_outcome,
    attach_kernel_forensics,
    derive_turn_outcome,
)
from personal_enigma.api.demo_orchestrator import LlmTrace


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
