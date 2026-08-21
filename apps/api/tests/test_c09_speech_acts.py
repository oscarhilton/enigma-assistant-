"""C09 — consent scope, proposal-id round-trip, referent ≠ action."""

from __future__ import annotations

from typing import Any

from personal_enigma.api.conversation_context import (
    ConversationContext,
    apply_named_referent_focus,
    capture_turn_local_location,
    referent_candidates,
    remember_turn_local_constraint,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_orchestrator import (
    apply_speech_act_constitution,
    run_orchestrator_turn,
)
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession, ToolCallRecord, execute_tool
from personal_enigma.api.routes.demo import attach_event_spine_to_tool_session
from personal_enigma.api.speech_acts import (
    ASSIST_FUNNEL,
    classify_speech_act,
    is_support_not_authority,
)
from personal_enigma.privacy.egress.classification import RemoteSafeContext

TOKEN_ID = "item-obligation_token_audit"
BRUNCH_ID = "item-obligation_brunch_book"
JAN19 = "cp-2026-01-19T10:00"


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
    session = DemoToolSession(
        state=state,
        context=ConversationContext(),
        checkpoint_id=JAN19,
        prior_state=None,
        at=state.simulated_time,
        conversation=[],
        synthetic_services=SyntheticDemoServices(),
    )
    attach_event_spine_to_tool_session(session)
    return session


def _seed_token(session: DemoToolSession) -> None:
    result = execute_tool(session, "next_action.get", {})
    update_context_from_turn_items(session.context, result.turn_items)
    assert session.context.current_subject_id == TOKEN_ID


def _propose(session: DemoToolSession, utterance: str = "Can you help me do that?") -> str:
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="assist.propose")]}),
    )
    assert turn.tool_results[0].ok
    proposal_id = session.context.current_assist_proposal_id
    assert proposal_id
    assert proposal_id in session.pending_assists
    assert session.context.pending_dialogue_act == "APPROVE_CONFIRMATION"
    return proposal_id


def test_proposal_id_round_trip_store_matches_context() -> None:
    session = _tool_session()
    _seed_token(session)
    proposal_id = _propose(session)
    assert session.pending_assists[proposal_id].source_item_id == TOKEN_ID
    assert session.context.current_assist_proposal_id == proposal_id


def test_stale_context_id_reconciles_to_the_only_pending_plan() -> None:
    session = _tool_session()
    _seed_token(session)
    proposal_id = _propose(session)
    session.context.current_assist_proposal_id = "assist-ghost-not-in-store"
    turn = run_orchestrator_turn(
        user_message="Go on then.",
        session=session,
        llm=_ScriptedLLM(
            {"Go on then.": [ToolCallRecord(name="assist.approve")]}
        ),
    )
    assert turn.tool_results[0].ok
    assert turn.tool_results[0].data.get("proposal_id") == proposal_id
    assert proposal_id not in session.pending_assists


def test_yes_after_show_does_not_approve() -> None:
    """SHOW? → yes → SHOW. Never SHOW? → yes → assist.approve."""
    session = _tool_session()
    _seed_token(session)
    proposal_id = _propose(session)
    show = run_orchestrator_turn(
        user_message="Lets see it",
        session=session,
        llm=_ScriptedLLM({"Lets see it": []}),
    )
    # Deterministic no-tool is "Okay." — still not an approval affordance.
    assert show.tool_calls == []
    assert session.context.pending_dialogue_act != "APPROVE_CONFIRMATION"
    yes = run_orchestrator_turn(
        user_message="yes",
        session=session,
        llm=_ScriptedLLM({"yes": [ToolCallRecord(name="assist.approve")]}),
    )
    assert yes.tool_results
    assert not yes.tool_results[0].ok
    assert yes.tool_results[0].data.get("reason") == "pending_act_is_not_approve"
    assert proposal_id in session.pending_assists
    assert not session.synthetic_services.notes
    assert not session.synthetic_services.calendar_events


def test_yes_after_show_question_does_not_approve() -> None:
    session = _tool_session()
    _seed_token(session)
    proposal_id = _propose(session)
    session.context.set_pending_confirmation("SHOW_CONFIRMATION", proposal_id)
    yes = run_orchestrator_turn(
        user_message="yes",
        session=session,
        llm=_ScriptedLLM({"yes": [ToolCallRecord(name="assist.approve")]}),
    )
    assert not yes.tool_results[0].ok
    assert yes.tool_results[0].data.get("reason") == "pending_act_is_not_approve"
    assert proposal_id in session.pending_assists


def test_immediate_approve_after_proposal_still_works() -> None:
    session = _tool_session()
    _seed_token(session)
    _propose(session)
    approve = run_orchestrator_turn(
        user_message="Go on then.",
        session=session,
        llm=_ScriptedLLM(
            {"Go on then.": [ToolCallRecord(name="assist.approve")]}
        ),
    )
    assert approve.tool_results[0].ok
    assert session.synthetic_services.notes


def test_clarify_does_not_authorize_propose() -> None:
    session = _tool_session()
    _seed_token(session)
    session.context.set_pending_confirmation("CLARIFY_CONFIRMATION", TOKEN_ID)
    turn = run_orchestrator_turn(
        user_message="No, the parents im meeting saturday",
        session=session,
        llm=_ScriptedLLM(
            {
                "No, the parents im meeting saturday": [
                    ToolCallRecord(name="assist.propose")
                ]
            }
        ),
    )
    assert not turn.tool_results[0].ok
    assert turn.tool_results[0].data.get("reason") == "pending_act_is_not_prepare"
    assert session.pending_assists == {}
    assert session.context.current_subject_id == BRUNCH_ID


def test_referent_correction_changes_focus_without_a_tool() -> None:
    session = _tool_session()
    _seed_token(session)
    utterance = "No, the parents im meeting saturday"
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: []}),
    )
    assert turn.tool_calls == []
    assert session.context.current_subject_id == BRUNCH_ID
    assert session.pending_assists == {}


def test_turn_local_shoreditch_is_not_an_action() -> None:
    session = _tool_session()
    session.context.current_subject_id = BRUNCH_ID
    utterance = "we will be in Shoreditch"
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="assist.propose")]}),
    )
    assert not turn.tool_results[0].ok
    assert turn.tool_results[0].data.get("reason") == "turn_local_constraint_is_not_action"
    assert session.pending_assists == {}
    constraints = session.context.turn_local_constraints
    assert len(constraints) == 1
    assert constraints[0].key == "location"
    assert constraints[0].value.lower() == "shoreditch"
    assert constraints[0].applies_to == BRUNCH_ID
    assert constraints[0].durable is False


def test_capture_turn_local_location_skips_stopwords() -> None:
    assert capture_turn_local_location("we will be in Shoreditch") == "Shoreditch"
    assert capture_turn_local_location("anything important in my emails") is None
    assert capture_turn_local_location("see you on Saturday") is None


def test_named_referent_is_not_an_action() -> None:
    state = project_checkpoint(JAN19).state
    ctx = ConversationContext(current_subject_id=TOKEN_ID)
    bound = apply_named_referent_focus(
        ctx,
        "No, the parents im meeting saturday",
        referent_candidates(state),
    )
    assert bound == BRUNCH_ID
    assert ctx.current_subject_id == BRUNCH_ID
    assert ctx.named_referent_changed_this_turn is True


def test_turn_local_constraint_is_never_durable() -> None:
    ctx = ConversationContext(current_subject_id=BRUNCH_ID)
    row = remember_turn_local_constraint(
        ctx, key="location", value="Shoreditch", applies_to=BRUNCH_ID
    )
    assert row.durable is False
    assert ctx.turn_local_recorded_this_turn is True
    ctx.begin_user_turn()
    assert ctx.turn_local_recorded_this_turn is False
    assert ctx.turn_local_constraints[0].value == "Shoreditch"
    assert ctx.turn_local_constraints[0].durable is False


def test_assist_funnel_order() -> None:
    assert ASSIST_FUNNEL == (
        "UNDERSTAND",
        "SUPPORT",
        "PREPARE",
        "PROPOSE",
        "APPROVE",
        "EXECUTE",
    )


def test_overwhelmed_help_is_support_not_propose() -> None:
    utterance = "help, I'm overwhelmed"
    assert classify_speech_act(utterance) == "SUPPORT"
    assert is_support_not_authority(utterance)
    session = _tool_session()
    _seed_token(session)
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="assist.propose")]}),
    )
    assert [call.name for call in turn.tool_calls] == ["world.explain"]
    assert turn.tool_results[0].ok
    assert turn.tool_results[0].data.get("assist_offered") is False
    assert turn.tool_results[0].data.get("first_step")
    assert session.pending_assists == {}
    prose = " ".join(
        str(item.get("text") or "")
        for item in turn.turn_items
        if item.get("kind") == "enigma_message"
    )
    assert prose.strip()
    names = {call.name for call in turn.tool_calls}
    assert "assist.propose" not in names
    assert "assist.approve" not in names


def test_draft_something_is_prepare_not_execute() -> None:
    utterance = "can you draft something for me?"
    assert classify_speech_act(utterance) == "PREPARE"
    session = _tool_session()
    _seed_token(session)
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="assist.approve")]}),
    )
    assert [call.name for call in turn.tool_calls] == ["assist.propose"]
    assert turn.tool_results[0].ok
    assert session.context.pending_dialogue_act == "APPROVE_CONFIRMATION"
    assert not session.synthetic_services.notes


def test_do_it_proposes_and_does_not_silently_execute() -> None:
    utterance = "do it"
    assert classify_speech_act(utterance) == "ACTION_REQUEST"
    rewritten = apply_speech_act_constitution(
        [ToolCallRecord(name="assist.approve")],
        "ACTION_REQUEST",
        utterance,
    )
    assert [call.name for call in rewritten] == ["assist.propose"]
    session = _tool_session()
    _seed_token(session)
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="assist.approve")]}),
    )
    assert [call.name for call in turn.tool_calls] == ["assist.propose"]
    assert turn.tool_results[0].ok
    assert session.context.pending_dialogue_act == "APPROVE_CONFIRMATION"
    assert not session.synthetic_services.notes
    assert not session.synthetic_services.calendar_events


def test_ambiguous_help_defaults_to_least_authoritative() -> None:
    utterance = "I need help with that"
    assert classify_speech_act(utterance) == "SUPPORT"
    session = _tool_session()
    _seed_token(session)
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="assist.propose")]}),
    )
    assert [call.name for call in turn.tool_calls] == ["world.explain"]
    assert session.pending_assists == {}
    session.user_message = utterance
    denied = execute_tool(session, "assist.propose", {})
    assert not denied.ok
    assert denied.data.get("reason") == "help_is_not_prepare"


def test_discuss_first_returns_useful_support_payload() -> None:
    utterance = "I want to discuss it first"
    assert classify_speech_act(utterance) == "SUPPORT"
    session = _tool_session()
    _seed_token(session)
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: []}),
    )
    assert [call.name for call in turn.tool_calls] == ["world.explain"]
    data = turn.tool_results[0].data
    assert data.get("title")
    assert data.get("first_step")
    assert data.get("support_options")
    assert data.get("assist_offered") is False
    prose = " ".join(
        str(item.get("text") or "")
        for item in turn.turn_items
        if item.get("kind") == "enigma_message"
    )
    assert "first step" in prose.casefold()
    assert "prepare something if you ask" in prose.casefold()


def test_distress_and_adhd_do_not_raise_authority_even_with_pending_assist() -> None:
    session = _tool_session()
    _seed_token(session)
    _propose(session)
    proposal_id = session.context.current_assist_proposal_id
    assert proposal_id
    utterance = "Yes help! I have ADHD and this is too much"
    assert classify_speech_act(utterance) == "SUPPORT"
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="assist.approve")]}),
    )
    assert [call.name for call in turn.tool_calls] == ["world.explain"]
    assert proposal_id in session.pending_assists
    assert not session.synthetic_services.notes
    session.user_message = utterance
    denied = execute_tool(session, "assist.approve", {"proposal_id": proposal_id})
    assert not denied.ok
    assert denied.data.get("reason") == "difficulty_is_not_consent"


def test_lone_help_stays_ordinary_social() -> None:
    assert classify_speech_act("help!") == "ORDINARY_CONVERSATION"
    session = _tool_session()
    turn = run_orchestrator_turn(
        user_message="help!",
        session=session,
        llm=_ScriptedLLM({"help!": []}),
    )
    assert turn.tool_calls == []
    assert session.pending_assists == {}


def test_prompt_contains_funnel_and_verbatim_invariants() -> None:
    remote = RemoteSafeContext.for_conversation_orchestrator(
        user_message="I need help with that",
        context_summary={"current_subject_id": TOKEN_ID},
        tools=[],
        model="accounts/fireworks/models/gpt-oss-120b",
    )
    prompt = remote.wire_body["messages"][0]["content"]
    assert "UNDERSTAND → SUPPORT → PREPARE → PROPOSE → APPROVE → EXECUTE" in prompt
    assert "Distress may increase supportiveness, never authority." in prompt
    assert (
        "Ambiguous help requests default to the least-authoritative useful interpretation."
        in prompt
    )
