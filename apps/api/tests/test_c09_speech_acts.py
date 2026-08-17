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
from personal_enigma.api.demo_orchestrator import run_orchestrator_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession, ToolCallRecord, execute_tool

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


def _propose(session: DemoToolSession, utterance: str = "help with that") -> str:
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
