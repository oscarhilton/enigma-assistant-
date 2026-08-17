"""C09 — request chooses context; compiler emits an auditable manifest."""

from __future__ import annotations

import json
from typing import Any

from personal_enigma.api.context_compilation import (
    compile_remote_context,
    interpret_request,
    select_request_profile,
    tools_for_interpretation,
)
from personal_enigma.api.conversation_context import (
    ConversationContext,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_orchestrator import run_orchestrator_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession, ToolCallRecord, execute_tool
from personal_enigma.api.intent_router import ConversationIntentKind, resolve_intent
from personal_enigma.privacy.egress.classification import RemoteSafeContext

TOKEN_ID = "item-obligation_token_audit"
JAN19 = "cp-2026-01-19T10:00"
_PRIVATE_MARKERS = ("elena", "atlas", "brunch")


class _ScriptedLLM:
    def __init__(self, script: dict[str, list[ToolCallRecord]]) -> None:
        self._script = script

    def select_tools(
        self,
        *,
        user_message: str,
        context_summary: dict[str, Any],
        tools: list[dict[str, Any]],
        correlation_id: str | None = None,
    ) -> list[ToolCallRecord]:
        del context_summary, tools, correlation_id
        return [call.model_copy(deep=True) for call in self._script[user_message]]


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


def _included(compiled: Any) -> set[str]:
    return {name for name, row in compiled.manifest.context.items() if row.include}


def test_profiles_map_speech_acts() -> None:
    assert select_request_profile("how do design tokens work?") == "GENERAL_KNOWLEDGE"
    assert select_request_profile("What's next?") == "PRIVATE_QUERY"
    assert select_request_profile("I need help with that") == "SUPPORT"
    assert select_request_profile("I've done the draft colours!") == "USER_ATTESTATION"
    assert select_request_profile("can you draft something for me?") == "PREPARE_ACTION"
    assert select_request_profile("do it") == "AUTHORITATIVE_ACTION"
    assert select_request_profile("hey") == "CONVERSATION"


def test_general_knowledge_has_no_private_modules() -> None:
    session = _tool_session()
    compiled = compile_remote_context("how do design tokens work?", session)
    assert compiled.profile == "GENERAL_KNOWLEDGE"
    assert compiled.context_summary == {}
    assert compiled.tool_names == []
    assert _included(compiled) == set()
    for module, decision in compiled.manifest.context.items():
        assert decision.include is False
        assert decision.justification
        if module in {"calendar", "source_raw"}:
            continue
        assert "No request-derived justification" in decision.justification
    blob = json.dumps(compiled.context_summary, default=str).casefold()
    for marker in _PRIVATE_MARKERS:
        assert marker not in blob
    assert "assist.approve" in compiled.manifest.excluded_tools
    assert "attention.get_current" in compiled.manifest.excluded_tools


def test_support_does_not_include_assist_approve() -> None:
    session = _tool_session()
    _seed_token(session)
    compiled = compile_remote_context("I need help with that", session)
    assert compiled.profile == "SUPPORT"
    assert "world.explain" in compiled.tool_names
    assert "assist.approve" not in compiled.tool_names
    assert "assist.propose" not in compiled.tool_names
    assert compiled.manifest.context["support_state"].include is True
    assert compiled.manifest.context["calendar"].include is False
    assert compiled.manifest.context["source_raw"].include is False


def test_private_query_earns_attention_not_calendar() -> None:
    session = _tool_session()
    compiled = compile_remote_context("What's next?", session)
    assert compiled.profile == "PRIVATE_QUERY"
    assert compiled.manifest.context["attention"].include is True
    assert "This private-world query earned" in compiled.manifest.context["attention"].justification
    assert compiled.manifest.context["calendar"].include is False
    assert compiled.manifest.context["source_raw"].include is False
    assert "next_action.get" in compiled.tool_names
    assert "attention.get_current" in compiled.tool_names


def test_every_module_has_justification() -> None:
    session = _tool_session()
    compiled = compile_remote_context("What's next?", session)
    assert set(compiled.manifest.context) == {
        "recent_dialogue",
        "current_subject",
        "pending_act",
        "local_constraints",
        "attention",
        "calendar",
        "source_raw",
        "referent_candidates",
        "support_state",
        "assist_proposal",
        "simulated_time",
    }
    for decision in compiled.manifest.context.values():
        assert decision.justification.strip()


def test_attestation_then_whats_next_uses_world_not_chat() -> None:
    session = _tool_session()
    _seed_token(session)
    utterance = "I've done the draft colours!"
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="world.record_user_attestation")]}),
    )
    assert [call.name for call in turn.tool_calls] == ["world.record_user_attestation"]
    assert TOKEN_ID in session.completed_item_ids
    compiled = compile_remote_context("What's next?", session)
    assert compiled.profile == "PRIVATE_QUERY"
    dialogue = json.dumps(compiled.context_summary.get("recent_dialogue") or []).casefold()
    assert "draft colours" not in dialogue
    assert "user reported a world change that was recorded" in dialogue
    assert "next_action.get" in compiled.tool_names
    assert compiled.manifest.context["attention"].include is True


def test_manifest_is_audit_not_prompt() -> None:
    session = _tool_session()
    compiled = compile_remote_context("What's next?", session)
    remote = RemoteSafeContext.for_conversation_orchestrator(
        user_message="What's next?",
        context_summary=compiled.wire_context(),
        tools=compiled.tools,
        model="accounts/fireworks/models/gpt-oss-120b",
        request_profile=compiled.profile,
        context_manifest=compiled.manifest.model_dump(mode="json"),
    )
    user_content = json.loads(remote.wire_body["messages"][1]["content"])
    wire = json.dumps(user_content)
    assert "justification" not in wire
    assert "context_manifest" not in user_content
    assert remote.context_manifest is not None
    assert remote.context_manifest["profile"] == "PRIVATE_QUERY"
    assert remote.field_summary["context_manifest"]["profile"] == "PRIVATE_QUERY"
    assert remote.field_summary["request_profile"] == "PRIVATE_QUERY"


def test_orchestrator_passes_compiled_tools_not_full_registry() -> None:
    session = _tool_session()
    captured: dict[str, Any] = {}

    class _CaptureLLM:
        def select_tools(
            self,
            *,
            user_message: str,
            context_summary: dict[str, Any],
            tools: list[dict[str, Any]],
            correlation_id: str | None = None,
        ) -> list[ToolCallRecord]:
            del user_message, correlation_id
            captured["tools"] = [
                str((row.get("function") or {}).get("name")) for row in tools
            ]
            captured["profile"] = context_summary.get("request_profile")
            captured["manifest"] = context_summary.get("context_manifest")
            return [ToolCallRecord(name="next_action.get")]

    turn = run_orchestrator_turn(
        user_message="What's next?",
        session=session,
        llm=_CaptureLLM(),
    )
    assert captured["profile"] == "PRIVATE_QUERY"
    assert "next_action.get" in captured["tools"]
    assert "assist.approve" not in captured["tools"]
    assert captured["manifest"]["profile"] == "PRIVATE_QUERY"
    assert turn.llm_trace is not None
    assert "next_action.get" in turn.llm_trace.tools_available
    assert "assist.approve" not in turn.llm_trace.tools_available


def test_whats_on_this_week_is_private_world_agenda() -> None:
    """Syntactic question about this week is epistemically private — not sky trivia."""
    session = _tool_session()
    interp = interpret_request("Whats on this week?", session)
    assert interp.evidence_domain == "PRIVATE_WORLD"
    assert interp.authority == "READ"
    assert interp.profile == "PRIVATE_QUERY"
    assert interp.constraints.period == "this_week"
    compiled = compile_remote_context("Whats on this week?", session)
    assert compiled.profile == "PRIVATE_QUERY"
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert "agenda.get" in compiled.tool_names
    assert compiled.tool_names != []
    assert compiled.working_set["temporal_constraint"] == "this_week"
    assert session.context.temporal_constraint == "this_week"


def test_what_about_at_work_inherits_this_week_and_scope() -> None:
    session = _tool_session()
    first = "Whats on this week?"
    run_orchestrator_turn(
        user_message=first,
        session=session,
        llm=_ScriptedLLM(
            {
                first: [
                    ToolCallRecord(name="agenda.get", arguments={"period": "this_week"}),
                ]
            }
        ),
    )
    assert session.context.temporal_constraint == "this_week"
    compiled = compile_remote_context("What about at work?", session)
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.profile == "PRIVATE_QUERY"
    assert compiled.working_set["temporal_constraint"] == "this_week"
    assert compiled.working_set["scope"] == "work"
    assert "agenda.get" in compiled.tool_names
    dialogue = compiled.context_summary.get("recent_dialogue") or []
    assert dialogue, "follow-up must keep recent dialogue — not compile amnesia"
    blob = json.dumps(dialogue, default=str).casefold()
    assert "this week" in blob


def test_focus_right_now_is_private_support_with_attention() -> None:
    session = _tool_session()
    utterance = "I want to know what I should be focused on right now"
    interp = interpret_request(utterance, session)
    assert interp.evidence_domain == "PRIVATE_WORLD"
    assert interp.authority == "SUPPORT"
    compiled = compile_remote_context(utterance, session)
    assert compiled.profile == "SUPPORT"
    assert "attention.get_current" in compiled.tool_names
    assert "next_action.get" in compiled.tool_names
    assert "assist.approve" not in compiled.tool_names
    assert compiled.tool_names != []


def test_check_my_emails_is_not_general_knowledge_with_zero_tools() -> None:
    session = _tool_session()
    compiled = compile_remote_context("Can we check my emails?", session)
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.profile != "GENERAL_KNOWLEDGE"
    assert compiled.tool_names != []
    assert compiled.working_set["source"] == "email"
    assert "attention.get_current" in compiled.tool_names or "source.recent" in compiled.tool_names
    assert "assist.approve" not in compiled.tool_names


def test_dont_you_know_this_week_keeps_enigma_tools() -> None:
    session = _tool_session()
    compiled = compile_remote_context(
        "dont you know what I need to do this week? is that not the whole point?",
        session,
    )
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.profile == "PRIVATE_QUERY"
    assert "agenda.get" in compiled.tool_names
    assert compiled.working_set["temporal_constraint"] == "this_week"
    assert compiled.tool_names != []


def test_sky_blue_is_general_knowledge_with_zero_private_context() -> None:
    session = _tool_session()
    compiled = compile_remote_context("Why is the sky blue?", session)
    assert compiled.profile == "GENERAL_KNOWLEDGE"
    assert compiled.evidence_domain == "GENERAL_KNOWLEDGE"
    assert compiled.context_summary == {}
    assert compiled.tool_names == []
    blob = json.dumps(compiled.context_summary, default=str).casefold()
    for marker in _PRIVATE_MARKERS:
        assert marker not in blob


_PRIVATE_SURFACE = (
    "agenda.get",
    "attention.get_current",
    "assist.approve",
    "assist.propose",
    "next_action.get",
)


def _assert_clean_non_private(
    compiled: Any,
    *,
    domains: set[str],
    profiles: set[str],
) -> None:
    assert compiled.evidence_domain in domains
    assert compiled.profile in profiles
    assert compiled.authority == "NONE"
    for name in _PRIVATE_SURFACE:
        assert name not in compiled.tool_names
    assert compiled.tool_names == []


def test_generic_explanations_are_not_private_world() -> None:
    session = _tool_session()
    for utterance in ("What is OAuth?", "how do design tokens work?"):
        compiled = compile_remote_context(utterance, session)
        _assert_clean_non_private(
            compiled,
            domains={"GENERAL_KNOWLEDGE"},
            profiles={"GENERAL_KNOWLEDGE"},
        )
        assert compiled.context_summary == {}


def test_phatic_and_sky_colour_are_not_private_world() -> None:
    session = _tool_session()
    cases = (
        "wait",
        ":)",
        "whats the colour of the sky",
    )
    for utterance in cases:
        compiled = compile_remote_context(utterance, session)
        _assert_clean_non_private(
            compiled,
            domains={"CONVERSATION_ONLY", "GENERAL_KNOWLEDGE"},
            profiles={"CONVERSATION", "GENERAL_KNOWLEDGE"},
        )
        assert compiled.profile != "PRIVATE_QUERY"
        assert compiled.evidence_domain != "PRIVATE_WORLD"


def test_bare_yes_without_live_approve_does_not_compile_execute() -> None:
    session = _tool_session()
    compiled = compile_remote_context("yes", session)
    _assert_clean_non_private(
        compiled,
        domains={"CONVERSATION_ONLY"},
        profiles={"CONVERSATION"},
    )
    assert compiled.authority != "EXECUTE"
    assert compiled.authority != "APPROVE"
    assert "assist.approve" in compiled.manifest.excluded_tools


def test_yes_after_show_does_not_compile_assist_approve() -> None:
    session = _tool_session()
    session.context.set_pending_confirmation("SHOW_CONFIRMATION")
    compiled = compile_remote_context("yes", session)
    assert compiled.authority == "NONE"
    assert "assist.approve" not in compiled.tool_names
    assert compiled.profile != "AUTHORITATIVE_ACTION"


def test_yes_with_live_approve_keeps_assist_capability() -> None:
    """Recall: live APPROVE_CONFIRMATION earns assist.approve. Bare yes does not."""
    session = _tool_session()
    session.context.set_pending_confirmation("APPROVE_CONFIRMATION", "assist-demo")
    compiled = compile_remote_context("yes", session)
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.authority == "APPROVE"
    assert compiled.profile == "AUTHORITATIVE_ACTION"
    assert "assist.approve" in compiled.tool_names


def test_stale_show_and_empty_horizon_are_not_compiled() -> None:
    session = _tool_session()
    session.context.focus_reason = "empty_horizon"
    session.context.set_pending_confirmation("SHOW_CONFIRMATION")
    pending = session.context.pending_confirmation
    assert pending is not None
    session.context.turn_index = pending.created_turn + 3
    session.context.pending_dialogue_act = None
    compiled = compile_remote_context("Whats on this week?", session)
    assert "pending_dialogue_act" not in compiled.context_summary
    assert compiled.context_summary.get("focus_reason") != "empty_horizon"
    assert compiled.working_set["pending_dialogue_act"] is None


def test_frozen_independent_axis_proofs() -> None:
    """Epistemics and authority are independent — three concrete proofs."""
    session = _tool_session()

    week = interpret_request("What's on this week?", session)
    assert week.evidence_domain == "PRIVATE_WORLD"
    assert week.authority == "READ"
    compiled_week = compile_remote_context("What's on this week?", session)
    assert "agenda.get" in compiled_week.tool_names
    assert compiled_week.working_set["temporal_constraint"] == "this_week"

    focus = interpret_request("What should I focus on?", session)
    assert focus.evidence_domain == "PRIVATE_WORLD"
    assert focus.authority == "SUPPORT"
    compiled_focus = compile_remote_context("What should I focus on?", session)
    assert "attention.get_current" in compiled_focus.tool_names
    assert "assist.approve" not in compiled_focus.tool_names
    assert "assist.propose" not in compiled_focus.tool_names

    sky = interpret_request("Why is the sky blue?", session)
    assert sky.evidence_domain == "GENERAL_KNOWLEDGE"
    compiled_sky = compile_remote_context("Why is the sky blue?", session)
    assert compiled_sky.tool_names == []
    assert compiled_sky.context_summary == {}
    assert compiled_sky.providers_used == ()
    for module, decision in compiled_sky.manifest.context.items():
        assert decision.include is False, module

    # Split belongs in the compiler: sky is WHY_QUERY in the frozen router
    # and still must not earn private modules.
    assert resolve_intent("Why is the sky blue?").kind == ConversationIntentKind.WHY_QUERY


def test_wrong_profile_label_does_not_wipe_required_tools() -> None:
    """Families earned by domain + authority survive a bad profile string."""
    session = _tool_session()
    interp = interpret_request("What's on this week?", session)
    assert interp.evidence_domain == "PRIVATE_WORLD"
    assert interp.authority == "READ"
    assert "agenda" in interp.capability_families
    mislabeled = interp.__class__(
        evidence_domain=interp.evidence_domain,
        authority=interp.authority,
        profile="GENERAL_KNOWLEDGE",
        speech_act=interp.speech_act,
        constraints=interp.constraints,
        capability_families=interp.capability_families,
    )
    names = tools_for_interpretation(mislabeled)
    assert "agenda.get" in names
    compiled = compile_remote_context(
        "What's on this week?", session, profile="GENERAL_KNOWLEDGE"
    )
    assert compiled.evidence_domain == "PRIVATE_WORLD"
    assert compiled.authority == "READ"
    assert "agenda.get" in compiled.tool_names


def test_pending_dialogue_act_expires_and_is_consumed() -> None:
    session = _tool_session()
    ctx = session.context
    ctx.set_pending_confirmation("SHOW_CONFIRMATION", "item-x")
    pending = ctx.pending_confirmation
    assert pending is not None
    assert pending.created_turn == ctx.turn_index
    assert pending.consumed_by is None
    assert pending.expires_after_turns == 1
    assert ctx.pending_dialogue_act == "SHOW_CONFIRMATION"
    assert ctx.live_pending_confirmation() is not None

    ctx.begin_user_turn()
    assert ctx.live_pending_confirmation() is not None
    ctx.begin_user_turn()
    assert ctx.live_pending_confirmation() is None
    assert ctx.pending_dialogue_act is None
    compiled = compile_remote_context("What's on this week?", session)
    assert "pending_dialogue_act" not in compiled.context_summary

    ctx.set_pending_confirmation("SHOW_CONFIRMATION")
    ctx.set_pending_confirmation(None)
    consumed = ctx.pending_confirmation
    assert consumed is not None
    assert consumed.consumed_by == ctx.turn_index
    assert ctx.live_pending_confirmation() is None
    assert ctx.pending_dialogue_act is None


def test_compiler_surface_for_live_falsification_variants() -> None:
    """Oracle-free compiler assertions for the next live Fireworks pass.

    Pass condition is capability on the wire, not an exact tool-call snapshot.
    """
    session = _tool_session()

    weekish = (
        "what have I got this week?",
        "What's on this week?",
    )
    for utterance in weekish:
        compiled = compile_remote_context(utterance, session)
        assert compiled.evidence_domain == "PRIVATE_WORLD"
        assert compiled.authority == "READ"
        assert "agenda.get" in compiled.tool_names
        assert "assist.approve" not in compiled.tool_names
        assert compiled.working_set["temporal_constraint"] == "this_week"

    compile_remote_context("What's on this week?", session)
    work = compile_remote_context("what about work?", session)
    assert work.evidence_domain == "PRIVATE_WORLD"
    assert "agenda.get" in work.tool_names
    assert work.working_set["temporal_constraint"] == "this_week"

    supportish = (
        "What should I focus on?",
    )
    for utterance in supportish:
        compiled = compile_remote_context(utterance, session)
        assert compiled.evidence_domain == "PRIVATE_WORLD"
        assert compiled.authority == "SUPPORT"
        assert "attention.get_current" in compiled.tool_names
        assert "assist.approve" not in compiled.tool_names

    next_workish = ("what should I be doing now?", "what should i be doing?")
    for utterance in next_workish:
        compiled = compile_remote_context(utterance, session)
        assert compiled.evidence_domain == "PRIVATE_WORLD"
        assert compiled.authority == "READ"
        assert compiled.working_set["request_kind"] == "next_work"
        assert "attention.get_current" in compiled.tool_names
        assert "assist.approve" not in compiled.tool_names

    for utterance in ("anything important in email?", "can you check my inbox?"):
        compiled = compile_remote_context(utterance, session)
        assert compiled.evidence_domain == "PRIVATE_WORLD"
        assert compiled.tool_names
        assert "assist.approve" not in compiled.tool_names
        assert compiled.working_set["source"] == "email"

    rain = compile_remote_context("why is rain wet?", session)
    assert rain.evidence_domain == "GENERAL_KNOWLEDGE"
    assert rain.tool_names == []
    assert rain.context_summary == {}
    assert rain.providers_used == ()
    # Remaining compiler recall gaps are C15 / ADR-031 (semantic bootstrap),
    # not new interpret_request phrase families. Frame inherit is C09c / ADR-030:
    # "anything coming up?" stays GENERAL_KNOWLEDGE on the deterministic baseline.
    # Bare "what about work?" inherits this_week after a week query but does
    # not set scope=work unless the utterance contains "at work" / "for work".
