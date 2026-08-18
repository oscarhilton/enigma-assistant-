"""C27 — handoff and turn contract stay below grounded evidence."""

from __future__ import annotations

from typing import Any

from personal_enigma.api.context_compilation import compile_remote_context
from personal_enigma.api.conversation_context import (
    ConversationCapsule,
    ConversationContext,
    LastToolOutcome,
    TurnHandoff,
)
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_orchestrator import run_orchestrator_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession, ToolCallRecord

JAN19 = "cp-2026-01-19T10:00"


class _ScriptedLLM:
    def __init__(self, script: dict[str, list[ToolCallRecord]]) -> None:
        self._script = script
        self.last_conversational_text: str | None = None

    def select_tools(
        self,
        *,
        user_message: str,
        context_summary: dict[str, Any],
        tools: list[dict[str, Any]],
        correlation_id: str | None = None,
    ) -> list[ToolCallRecord]:
        del context_summary, tools, correlation_id
        return [call.model_copy(deep=True) for call in self._script.get(user_message, [])]


def _tool_session() -> DemoToolSession:
    state = project_checkpoint(JAN19).state
    return DemoToolSession(
        state=state,
        context=ConversationContext(),
        checkpoint_id=JAN19,
        prior_state=None,
        at=state.simulated_time,
        conversation=[],
        synthetic_services=SyntheticDemoServices(),
    )


def _run(session: DemoToolSession, utterance: str, tools: list[str]) -> None:
    run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM(
            {
                utterance: [
                    ToolCallRecord.model_construct(name=name, arguments={}) for name in tools
                ]
            }
        ),
        bootstrap=None,
    )


def test_partial_mail_answer_builds_non_authoritative_handoff_and_contract() -> None:
    session = _tool_session()

    _run(
        session,
        "I need you to look at my mail and tell me whats important",
        ["source.recent"],
    )

    handoff = session.context.handoff
    assert handoff is not None
    assert handoff.current_goal == "important_from_source"
    assert "checked source recency" in handoff.progress_made
    assert "which item actually matters remains unresolved" in handoff.unresolved
    assert "attention" in handoff.evidence_needed
    assert "dialogue residue is not evidence" in handoff.caveats

    compiled = compile_remote_context("and?", session)
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.authority == "READ"
    assert "attention.get_current" in compiled.tool_names

    summary_handoff = compiled.context_summary.get("conversation_handoff")
    assert isinstance(summary_handoff, dict)
    assert summary_handoff["current_goal"] == "important_from_source"
    assert "attention" in summary_handoff["evidence_needed"]

    contract = compiled.context_summary.get("turn_contract")
    assert isinstance(contract, dict)
    assert contract["request_kind"] == "important_from_source"
    assert contract["current_satisfaction"] == "partial"
    assert "attention" in contract["evidence_still_obtainable"]
    assert contract["authority_level"] == "READ"
    assert contract["factual_precedence"] == [
        "WORLD_OR_GROUNDED_EVIDENCE",
        "TURN_CONTRACT",
        "CAPSULE",
        "HANDOFF",
        "DIALOGUE",
    ]
    assert "ask if the referent is unresolved before claiming private facts" in contract[
        "stop_ask_conditions"
    ]


def test_freeze_gate_repair_turns_keep_goal_without_dialogue_becoming_truth() -> None:
    session = _tool_session()
    _run(
        session,
        "I need you to look at my mail and tell me whats important",
        ["source.recent"],
    )

    compiled = compile_remote_context("ffs", session)

    assert compiled.profile == "PRIVATE_QUERY"
    assert compiled.working_set["request_kind"] == "important_from_source"
    assert compiled.working_set["handoff"]["current_goal"] == "important_from_source"
    assert "attention.get_current" in compiled.tool_names
    assert "source.recent" in compiled.tool_names
    assert (
        compiled.working_set["turn_contract"]["factual_precedence"][0]
        == "WORLD_OR_GROUNDED_EVIDENCE"
    )

    blob = str(compiled.working_set).casefold()
    assert "kickoff" not in blob
    assert "meeting second" not in blob


def test_turn_contract_does_not_inherit_approval_authority() -> None:
    session = _tool_session()

    _run(session, "Can you help me do that?", ["assist.propose"])
    compiled = compile_remote_context("and?", session)

    contract = compiled.context_summary.get("turn_contract")
    assert isinstance(contract, dict)
    assert contract["authority_level"] != "APPROVE"
    assert "assist.approve" not in contract["capabilities_available"]
    assert "explicit approval must be re-earned this turn" not in contract[
        "approval_requirements"
    ]


def test_stale_investigating_handoff_cannot_override_fresher_capsule_resolution() -> None:
    session = _tool_session()
    session.context.capsule = ConversationCapsule(
        evidence_domain="PRIVATE_WORLD",
        active_goal=None,
        unresolved_request=None,
        last_outcome=LastToolOutcome(capability="attention.get_current", request_satisfied=True),
        frame_created_turn=session.context.turn_index,
        frame_expires_after_turns=6,
    )
    session.context.handoff = TurnHandoff(
        current_goal="next_work",
        progress_made=("checked current attention",),
        unresolved=("next work recommendation remains unresolved",),
        evidence_needed=("attention",),
        natural_continuation="Fetch grounded next-work evidence before answering.",
        caveats=("handoff is continuity only, not factual authority",),
    )

    compiled = compile_remote_context("what should i be doing?", session)

    contract = compiled.context_summary.get("turn_contract")
    assert isinstance(contract, dict)
    assert contract["current_satisfaction"] == "satisfied"
    assert "handoff_progress" not in contract["evidence_available"]


def test_handoff_progress_alone_does_not_authorize_factual_satisfaction() -> None:
    session = _tool_session()
    session.context.handoff = TurnHandoff(
        current_goal="next_work",
        progress_made=("checked current attention",),
        unresolved=(),
        evidence_needed=("attention",),
        natural_continuation="Fetch grounded next-work evidence before answering.",
        caveats=(
            "handoff is continuity only, not factual authority",
            "missing evidence must be fetched before completing the answer",
        ),
    )

    compiled = compile_remote_context("what should i be doing?", session)

    contract = compiled.context_summary.get("turn_contract")
    assert isinstance(contract, dict)
    assert contract["current_satisfaction"] == "unknown"
    assert "handoff_progress" not in contract["evidence_available"]
