"""C09c — compile the conversation, not just the sentence."""

from __future__ import annotations

import json
from typing import Any

from personal_enigma.api.context_compilation import compile_remote_context, interpret_request
from personal_enigma.api.conversation_context import (
    ConversationCapsule,
    ConversationContext,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_orchestrator import run_orchestrator_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession, ToolCallRecord, execute_tool

TOKEN_ID = "item-obligation_token_audit"
JAN19 = "cp-2026-01-19T10:00"
_PRIVATE_MARKERS = ("elena@", "raw email", "verbatim")


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


def _seed_token(session: DemoToolSession) -> None:
    result = execute_tool(session, "next_action.get", {})
    update_context_from_turn_items(session.context, result.turn_items)
    assert session.context.current_subject_id == TOKEN_ID


def _run(session: DemoToolSession, utterance: str, tools: list[str]) -> Any:
    script = {utterance: [ToolCallRecord(name=name) for name in tools]}
    return run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM(script),
    )


def test_agenda_satisfied_does_not_clear_private_frame() -> None:
    session = _tool_session()
    turn = _run(session, "what's on today?", ["agenda.get"])
    assert turn.tool_calls[0].name == "agenda.get"
    capsule = session.context.live_grounded_frame()
    assert capsule is not None
    assert capsule.evidence_domain == "PRIVATE_WORLD"
    assert capsule.temporal_constraint == "today"
    assert capsule.unresolved_request is None
    assert capsule.active_goal is None
    assert capsule.last_outcome is not None
    assert capsule.last_outcome.request_satisfied is True


def test_free_time_inherits_today_private_frame() -> None:
    session = _tool_session()
    _run(session, "what's on today?", ["agenda.get"])
    utterance = "what should I do with this free time?"
    interp = interpret_request(utterance, session)
    assert interp.evidence_domain == "PRIVATE_WORLD"
    assert interp.profile != "GENERAL_KNOWLEDGE"
    assert interp.authority in {"READ", "SUPPORT"}
    assert interp.authority != "APPROVE"
    compiled = compile_remote_context(utterance, session)
    assert compiled.working_set["temporal_constraint"] == "today"
    tools = compiled.tool_names
    assert "attention.get_current" in tools or "next_action.get" in tools
    assert "agenda.get" in compiled.tool_names or "next_action.get" in compiled.tool_names


def test_cant_remember_project_is_support_around_token() -> None:
    """Existing SUPPORT path around TOKEN. Do not enrich world.explain."""
    session = _tool_session()
    _seed_token(session)
    _run(session, "what's on today?", ["agenda.get"])
    utterance = "I can't remember what this project is about"
    compiled = compile_remote_context(utterance, session)
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.authority == "SUPPORT"
    assert compiled.profile == "SUPPORT"
    assert compiled.tool_names
    assert "assist.approve" not in compiled.tool_names
    assert "assist.propose" not in compiled.tool_names
    assert session.context.current_subject_id == TOKEN_ID


def test_who_do_i_ask_keeps_token_private_support() -> None:
    session = _tool_session()
    _seed_token(session)
    _run(session, "what's on today?", ["agenda.get"])
    utterance = "who do I ask for help?"
    compiled = compile_remote_context(utterance, session)
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.authority == "SUPPORT"
    assert compiled.tool_names
    assert "assist.approve" not in compiled.tool_names
    assert session.context.current_subject_id == TOKEN_ID


def test_attestation_request_dies_frame_lives() -> None:
    session = _tool_session()
    _seed_token(session)
    turn = _run(session, "I've done the design work", ["world.record_user_attestation"])
    assert turn.tool_calls[0].name == "world.record_user_attestation"
    assert TOKEN_ID in session.completed_item_ids
    capsule = session.context.live_grounded_frame()
    assert capsule is not None
    assert capsule.current_subject_id == TOKEN_ID or session.context.current_subject_id == TOKEN_ID
    assert capsule.active_goal is None
    assert capsule.unresolved_request is None
    assert capsule.last_outcome is not None
    assert capsule.last_outcome.request_satisfied is True
    blob = json.dumps(capsule.public_view(), default=str).casefold()
    assert "completed" not in blob
    assert "user_attested" not in blob

    follow = "what else is on?"
    interp = interpret_request(follow, session)
    assert interp.evidence_domain == "PRIVATE_WORLD"
    assert interp.authority == "READ"
    assert interp.request_kind in {"agenda", "next_work"}
    assert interp.request_kind != "attest"
    compiled = compile_remote_context(follow, session)
    assert compiled.profile == "PRIVATE_QUERY"
    assert "agenda.get" in compiled.tool_names or "next_action.get" in compiled.tool_names
    assert "world.record_user_attestation" not in compiled.tool_names


def test_any_other_tasks_stays_private() -> None:
    session = _tool_session()
    _run(session, "what's on today?", ["agenda.get"])
    compiled = compile_remote_context("any other tasks?", session)
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    tools = compiled.tool_names
    assert tools
    assert "next_action.get" in tools or "attention.get_current" in tools


def test_mail_partial_then_repair_requires_fresh_private_tool() -> None:
    session = _tool_session()
    mail = "look at my mail and tell me what's important"
    turn = _run(session, mail, ["source.recent"])
    assert turn.tool_calls[0].name == "source.recent"
    capsule = session.context.live_grounded_frame()
    assert capsule is not None
    assert capsule.unresolved_request is not None
    assert capsule.unresolved_request.kind == "important_from_source"
    assert capsule.unresolved_request.status == "PARTIAL"
    assert capsule.last_outcome is not None
    assert capsule.last_outcome.capability == "source.recent"
    assert capsule.last_outcome.request_satisfied is False

    and_turn = "and?"
    compiled_and = compile_remote_context(and_turn, session)
    assert compiled_and.evidence_domain == "PRIVATE_WORLD"
    assert compiled_and.tool_names
    _run(session, and_turn, ["source.recent"])

    next_work = "WHAT I AM WORKING ON NEXT!"
    compiled_next = compile_remote_context(next_work, session)
    assert compiled_next.evidence_domain == "PRIVATE_WORLD"
    assert compiled_next.profile != "GENERAL_KNOWLEDGE"
    _run(session, next_work, ["attention.get_current"])

    ffs = "ffs"
    compiled_ffs = compile_remote_context(ffs, session)
    assert compiled_ffs.evidence_domain == "PRIVATE_WORLD"
    assert compiled_ffs.profile != "CONVERSATION"
    assert compiled_ffs.tool_names
    private_tools = {"attention.get_current", "next_action.get", "agenda.get"}
    assert private_tools & set(compiled_ffs.tool_names)
    ffs_turn = _run(session, ffs, ["attention.get_current"])
    assert [row.name for row in ffs_turn.tool_results if row.ok] == ["attention.get_current"]
    wire = json.dumps(compiled_ffs.working_set, default=str).casefold()
    for marker in _PRIVATE_MARKERS:
        assert marker not in wire


def test_ffs_without_tool_does_not_satisfy_private_request() -> None:
    """Capsule may recover the question. Transcript is not the answer."""
    session = _tool_session()
    _run(session, "look at my mail and tell me what's important", ["source.recent"])
    llm = _ScriptedLLM({"ffs": []})
    llm.last_conversational_text = (
        "Token audit kickoff first, token meeting second, Q1 checkout third."
    )
    run_orchestrator_turn(user_message="ffs", session=session, llm=llm)
    capsule = session.context.live_grounded_frame()
    assert capsule is not None
    assert capsule.unresolved_request is not None
    assert capsule.last_outcome is None or capsule.last_outcome.request_satisfied is False


def test_sky_blue_contradicts_and_clears_private_modules() -> None:
    session = _tool_session()
    _run(session, "what's on today?", ["agenda.get"])
    compiled = compile_remote_context("why is the sky blue?", session)
    assert compiled.evidence_domain == "GENERAL_KNOWLEDGE"
    assert compiled.tool_names == []
    assert compiled.context_summary == {}
    _run(session, "why is the sky blue?", [])
    assert session.context.live_grounded_frame() is None


def test_approve_authority_is_not_inherited() -> None:
    session = _tool_session()
    session.context.set_pending_confirmation("APPROVE_CONFIRMATION", TOKEN_ID)
    session.context.capsule = ConversationCapsule(
        previous_authority="APPROVE",
        evidence_domain="PRIVATE_WORLD",
        temporal_constraint="today",
        frame_created_turn=session.context.turn_index,
        frame_expires_after_turns=6,
    )
    compiled = compile_remote_context("And the other one?", session)
    assert compiled.authority != "APPROVE"
    assert compiled.authority != "EXECUTE"
    assert compiled.authority != "PREPARE"
    assert "assist.approve" not in compiled.tool_names


def test_capsule_wire_payload_has_no_raw_private_bodies() -> None:
    session = _tool_session()
    _run(session, "look at my mail and tell me what's important", ["source.recent"])
    compiled = compile_remote_context("and?", session)
    blob = json.dumps(
        {"summary": compiled.context_summary, "working_set": compiled.working_set},
        default=str,
    ).casefold()
    assert "justification" not in blob
    assert "providers" not in compiled.working_set
    assert "tools" not in compiled.working_set
    assert "capability_families" not in compiled.working_set
    assert "previous_authority" not in (compiled.working_set.get("capsule") or {})
    for marker in ("raw email bodies", "verbatim", "@"):
        assert marker not in blob
