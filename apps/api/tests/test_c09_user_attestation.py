"""C09 — user reports write world evidence. Conversation is not the only place."""

from __future__ import annotations

from typing import Any

from personal_enigma.api.conversation_context import (
    ConversationContext,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_orchestrator import run_orchestrator_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession, ToolCallRecord, execute_tool
from personal_enigma.api.speech_acts import classify_speech_act

TOKEN_ID = "item-obligation_token_audit"
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
    assert session.context.current_next_action_id


def _next_action_ids(result: Any) -> list[str]:
    ids = [
        (row.get("source_candidate_id") or row.get("id"))
        for row in result.data.get("next_actions", [])
        if isinstance(row, dict)
    ]
    if ids:
        return ids
    return [
        item["action"]["source_candidate_id"]
        for item in result.turn_items
        if item.get("kind") == "next_action"
    ]


def _attest_token_done(
    session: DemoToolSession,
    utterance: str = "I've done the draft colours!",
) -> None:
    run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="world.record_user_attestation")]}),
    )
    assert TOKEN_ID in session.completed_item_ids


def test_done_the_draft_colours_is_user_attestation() -> None:
    assert classify_speech_act("I've done the draft colours!") == "USER_ATTESTATION"
    assert classify_speech_act("I booked it") == "USER_ATTESTATION"
    assert classify_speech_act("Book it") == "ACTION_REQUEST"


def test_attestation_writes_evidence_and_clears_next_action() -> None:
    session = _tool_session()
    _seed_token(session)
    utterance = "I've done the draft colours!"
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="next_action.get")]}),
    )
    assert [call.name for call in turn.tool_calls] == ["world.record_user_attestation"]
    assert turn.tool_results[0].ok
    assert turn.tool_results[0].data.get("evidence") == "USER_ATTESTED"
    assert turn.tool_results[0].data.get("source") == "user_attestation"
    assert turn.tool_results[0].data.get("state") == "COMPLETED"
    assert turn.tool_results[0].data.get("target_id") == TOKEN_ID
    assert TOKEN_ID in session.completed_item_ids
    assert session.context.current_subject_id == TOKEN_ID
    assert session.context.current_next_action_id is None
    assert session.pending_assists == {}
    assert not session.synthetic_services.notes
    nxt = execute_tool(session, "next_action.get", {})
    ids = [
        (row.get("source_candidate_id") or row.get("id"))
        for row in nxt.data.get("next_actions", [])
        if isinstance(row, dict)
    ]
    if not ids:
        ids = [
            item["action"]["source_candidate_id"]
            for item in nxt.turn_items
            if item.get("kind") == "next_action"
        ]
    assert TOKEN_ID not in ids


def test_attestation_is_not_assist_even_if_model_proposes() -> None:
    session = _tool_session()
    _seed_token(session)
    utterance = "I've finished it!"
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="assist.propose")]}),
    )
    assert [call.name for call in turn.tool_calls] == ["world.record_user_attestation"]
    assert session.pending_assists == {}


def test_social_follow_up_does_not_mutate_again() -> None:
    session = _tool_session()
    _seed_token(session)
    done = "I've done the draft colours!"
    run_orchestrator_turn(
        user_message=done,
        session=session,
        llm=_ScriptedLLM({done: [ToolCallRecord(name="world.record_user_attestation")]}),
    )
    attest_count = len(session.attestations)
    happy = "Aren't you happy for me?"
    turn = run_orchestrator_turn(
        user_message=happy,
        session=session,
        llm=_ScriptedLLM({happy: []}),
    )
    assert turn.tool_calls == []
    assert len(session.attestations) == attest_count
    assert session.context.current_subject_id == TOKEN_ID


def test_superseding_open_restores_token_as_actionable() -> None:
    session = _tool_session()
    _seed_token(session)
    done = "I've done the draft colours!"
    run_orchestrator_turn(
        user_message=done,
        session=session,
        llm=_ScriptedLLM({done: [ToolCallRecord(name="world.record_user_attestation")]}),
    )
    prior_id = session.attestations[-1].id
    reopen = "Actually, sorry, I haven't finished it."
    turn = run_orchestrator_turn(
        user_message=reopen,
        session=session,
        llm=_ScriptedLLM({reopen: [ToolCallRecord(name="world.record_user_attestation")]}),
    )
    assert turn.tool_results[0].data.get("state") == "OPEN"
    assert turn.tool_results[0].data.get("supersedes") == prior_id
    assert TOKEN_ID not in session.completed_item_ids
    nxt = execute_tool(session, "next_action.get", {})
    assert TOKEN_ID in _next_action_ids(nxt)


def test_attestation_survives_intervening_agenda_and_subject() -> None:
    session = _tool_session()
    _seed_token(session)
    _attest_token_done(session)

    agenda = execute_tool(session, "agenda.get", {"period": "today"})
    agenda_ids = [
        (row.get("source_candidate_id") or row.get("id"))
        for row in agenda.data.get("next_actions", [])
        if isinstance(row, dict)
    ]
    assert TOKEN_ID not in agenda_ids
    assert "Draft colour + spacing token inventory" not in str(agenda.turn_items)

    execute_tool(session, "attention.get_current", {})
    nxt = execute_tool(session, "next_action.get", {})
    assert TOKEN_ID not in _next_action_ids(nxt)
    assert session.context.current_next_action_id != "next-item-obligation_token_audit"


def test_next_action_get_reoverlays_stale_frozen_state() -> None:
    """Do not answer next_action.get from a pre-attestation cache."""
    session = _tool_session()
    _seed_token(session)
    _attest_token_done(session)
    session.state = project_checkpoint(JAN19).state
    session.base_state = None
    nxt = execute_tool(session, "next_action.get", {})
    assert TOKEN_ID not in _next_action_ids(nxt)
    alt = execute_tool(session, "next_action.get_alternatives", {})
    alternate = alt.data.get("alternate") or {}
    assert (alternate.get("source_candidate_id") or alternate.get("id")) != TOKEN_ID


def test_attested_completion_survives_checkpoint_reprojection(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.delenv("ENIGMA_DEMO_LLM_CONVERSATION", raising=False)
    monkeypatch.delenv("LLM_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    from personal_enigma.api.routes.demo import DemoSession

    demo = DemoSession()
    tool = DemoToolSession(
        state=demo._attention_state(),
        context=demo.conversation_context,
        checkpoint_id=demo.checkpoint_id,
        prior_state=None,
        at=demo._attention_state().simulated_time,
        conversation=demo.conversation,
        completed_item_ids=demo.completed_item_ids,
        assist_advances=demo.assist_advances,
        attestations=demo.attestations,
        synthetic_services=demo.synthetic_services,
        base_state=project_checkpoint(JAN19).state,
    )
    _seed_token(tool)
    _attest_token_done(tool)
    assert TOKEN_ID in demo.completed_item_ids
    demo.jump_checkpoint("cp-2026-01-20T11:00")
    assert TOKEN_ID in demo.completed_item_ids
    live = {row.source_candidate_id or row.id for row in demo._attention_state().next_actions}
    assert TOKEN_ID not in live
    stale = DemoToolSession(
        state=project_checkpoint("cp-2026-01-20T11:00").state,
        context=demo.conversation_context,
        checkpoint_id="cp-2026-01-20T11:00",
        prior_state=None,
        at=demo._attention_state().simulated_time,
        conversation=demo.conversation,
        completed_item_ids=demo.completed_item_ids,
        assist_advances=demo.assist_advances,
        attestations=demo.attestations,
        synthetic_services=demo.synthetic_services,
    )
    nxt = execute_tool(stale, "next_action.get", {})
    assert TOKEN_ID not in _next_action_ids(nxt)


def test_open_after_checkpoint_reprojection_restores_token(
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.delenv("ENIGMA_DEMO_LLM_CONVERSATION", raising=False)
    monkeypatch.delenv("LLM_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    from personal_enigma.api.routes.demo import DemoSession

    demo = DemoSession()
    tool = DemoToolSession(
        state=demo._attention_state(),
        context=demo.conversation_context,
        checkpoint_id=demo.checkpoint_id,
        prior_state=None,
        at=demo._attention_state().simulated_time,
        conversation=demo.conversation,
        completed_item_ids=demo.completed_item_ids,
        assist_advances=demo.assist_advances,
        attestations=demo.attestations,
        synthetic_services=demo.synthetic_services,
        base_state=project_checkpoint(JAN19).state,
    )
    _seed_token(tool)
    _attest_token_done(tool)
    demo.jump_checkpoint("cp-2026-01-20T11:00")
    tool.checkpoint_id = "cp-2026-01-20T11:00"
    tool.base_state = None
    tool.at = demo._attention_state().simulated_time
    reopen = "Actually, sorry, I haven't finished the token inventory."
    turn = run_orchestrator_turn(
        user_message=reopen,
        session=tool,
        llm=_ScriptedLLM({reopen: [ToolCallRecord(name="world.record_user_attestation")]}),
    )
    assert turn.tool_results[0].data.get("state") == "OPEN"
    assert TOKEN_ID not in demo.completed_item_ids
    nxt = execute_tool(tool, "next_action.get", {})
    assert TOKEN_ID in _next_action_ids(nxt)
