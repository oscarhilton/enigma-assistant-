"""C09 — paraphrase invariance without production phrase maps.

Harness tests (this file + test_c09_conversation_benchmark.py) prove the
architecture *around* the model. Phrase maps / IntentOracleLLM are scaffolding
and a test oracle — not LLM victory.

Live Fireworks proof: ``test_c09_live_fireworks_paraphrase`` (skip unless
``ENIGMA_C09_LIVE=1`` and ``FIREWORKS_API_KEY``). Graduation is unmet until a
real model passes the off-script chain with tool+id assertions.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from personal_enigma.api.conversation_context import (
    ConversationContext,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_orchestrator import (
    EgressConversationLLM,
    IntentOracleLLM,
    run_orchestrator_turn,
    tool_calls_from_intent,
)
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession, ToolCallRecord, execute_tool

TASK_TOKEN_AUDIT = "item-obligation_token_audit"
BRUNCH_ID = "item-obligation_brunch_book"
JAN19 = "cp-2026-01-19T10:00"

UTTER_ASSIST = "Let's get cracking on that."
UTTER_EXPLAIN = "Why bother?"
UTTER_ALTERNATIVE = "Nah. Give me something less tedious."
UTTER_DURATION = "How long's that one?"
UTTER_FIT = "Can I squeeze it in?"
UTTER_RECOVERY = "No, I meant the token thing."
UTTER_UNSUPPORTED = "Where did I leave my keys?"

# Test expectation only — not imported by demo_orchestrator / intent_router.
PARAPHRASE_EXPECTED_TOOLS: dict[str, list[ToolCallRecord]] = {
    UTTER_ASSIST: [ToolCallRecord(name="assist.propose")],
    UTTER_EXPLAIN: [ToolCallRecord(name="world.explain")],
    UTTER_ALTERNATIVE: [
        ToolCallRecord(name="next_action.reject"),
        ToolCallRecord(name="next_action.get_alternatives"),
    ],
    UTTER_DURATION: [ToolCallRecord(name="referent.get_duration")],
    UTTER_FIT: [
        ToolCallRecord(name="availability.check", arguments={"duration_minutes": 15}),
    ],
    UTTER_RECOVERY: [
        ToolCallRecord(name="world.explain", arguments={"target": TASK_TOKEN_AUDIT}),
    ],
}

PARAPHRASE_TRANSCRIPT = (
    UTTER_ASSIST,
    UTTER_EXPLAIN,
    UTTER_ALTERNATIVE,
    UTTER_DURATION,
    UTTER_FIT,
)


def _c09_live_enabled() -> bool:
    flag = os.environ.get("ENIGMA_C09_LIVE", "").lower() in ("1", "true", "yes")
    return flag and bool(os.environ.get("FIREWORKS_API_KEY"))


def _c09_live_reps() -> int:
    raw = os.environ.get("ENIGMA_C09_LIVE_REPS", "3")
    try:
        reps = int(raw)
    except ValueError:
        reps = 3
    return max(3, min(5, reps))


class ScriptedConversationLLM:
    """Test double — returns fixture tool calls. Does not use production phrase maps."""

    def __init__(self, script: dict[str, list[ToolCallRecord]] | None = None) -> None:
        self._script = script if script is not None else PARAPHRASE_EXPECTED_TOOLS

    def select_tools(
        self,
        *,
        user_message: str,
        context_summary: dict[str, Any],
        tools: list[dict[str, Any]],
        correlation_id: str | None = None,
    ) -> list[ToolCallRecord]:
        del context_summary, tools, correlation_id
        if user_message not in self._script:
            raise AssertionError(f"unscripted utterance (not a production map): {user_message!r}")
        return [call.model_copy(deep=True) for call in self._script[user_message]]


def _tool_session(checkpoint_id: str = JAN19) -> DemoToolSession:
    state = project_checkpoint(checkpoint_id).state
    return DemoToolSession(
        state=state,
        context=ConversationContext(),
        checkpoint_id=checkpoint_id,
        prior_state=None,
        at=state.simulated_time,
        conversation=[],
        synthetic_services=SyntheticDemoServices(),
    )


def _seed_token_next_action(session: DemoToolSession) -> None:
    result = execute_tool(session, "next_action.get", {})
    update_context_from_turn_items(session.context, result.turn_items)
    assert session.context.current_subject_id == TASK_TOKEN_AUDIT


def _explain_brunch_wrong_subject(session: DemoToolSession) -> None:
    session.context.current_subject_id = BRUNCH_ID
    session.context.current_attention_item_id = BRUNCH_ID
    session.context.current_subject_kind = "attention_item"
    session.context.current_next_action_id = None
    result = execute_tool(session, "world.explain", {})
    update_context_from_turn_items(session.context, result.turn_items)
    items = [item for item in result.turn_items if item["kind"] == "attention_item"]
    assert items
    assert items[0]["item"]["id"] == BRUNCH_ID
    assert session.context.current_subject_id == BRUNCH_ID


def _tool_names(turn: Any) -> list[str]:
    return [call.name for call in turn.tool_calls]


def _require_tool(turn: Any, name: str) -> ToolCallRecord:
    matching = [call for call in turn.tool_calls if call.name == name]
    assert matching, f"expected tool {name!r}, got {_tool_names(turn)}"
    return matching[0]


@pytest.mark.parametrize("utterance", PARAPHRASE_TRANSCRIPT)
def test_paraphrases_not_covered_by_production_phrase_map(utterance: str) -> None:
    """Oracle/router must not secretly win these — they are off the phrase map."""
    expected = [call.name for call in PARAPHRASE_EXPECTED_TOOLS[utterance]]
    oracle = [call.name for call in tool_calls_from_intent(utterance)]
    assert oracle != expected
    assert IntentOracleLLM().select_tools(
        user_message=utterance,
        context_summary={},
        tools=[],
    ) == tool_calls_from_intent(utterance)


def test_scripted_llm_does_not_use_production_phrase_map() -> None:
    names = ScriptedConversationLLM.select_tools.__code__.co_names
    assert "tool_calls_from_intent" not in names
    assert "IntentOracleLLM" not in names


def test_paraphrase_transcript_same_tools_and_referents_as_canonical() -> None:
    """Wiring proof: expected tools → same referents as the C09 canonical transcript."""
    session = _tool_session()
    _seed_token_next_action(session)
    llm = ScriptedConversationLLM()

    start = run_orchestrator_turn(
        user_message=UTTER_ASSIST,
        session=session,
        llm=llm,
    )
    assert _tool_names(start) == ["assist.propose"]
    plans = list(session.pending_assists.values())
    assert plans
    assert plans[0].source_item_id == TASK_TOKEN_AUDIT
    assert session.context.current_subject_id == TASK_TOKEN_AUDIT

    why = run_orchestrator_turn(
        user_message=UTTER_EXPLAIN,
        session=session,
        llm=llm,
    )
    assert _tool_names(why) == ["world.explain"]
    assert why.tool_results[0].data.get("subject_id") == TASK_TOKEN_AUDIT
    assert session.context.current_subject_id == TASK_TOKEN_AUDIT
    why_items = [item for item in why.turn_items if item.get("kind") == "attention_item"]
    assert why_items
    assert why_items[0]["item"]["id"] != BRUNCH_ID

    reject_alt = run_orchestrator_turn(
        user_message=UTTER_ALTERNATIVE,
        session=session,
        llm=llm,
    )
    assert _tool_names(reject_alt) == [
        "next_action.reject",
        "next_action.get_alternatives",
    ]
    alt_items = [item for item in reject_alt.turn_items if item["kind"] == "next_action"]
    assert alt_items
    alt_id = alt_items[0]["action"]["source_candidate_id"]
    assert alt_id != TASK_TOKEN_AUDIT
    assert session.context.current_subject_id == alt_id

    duration = run_orchestrator_turn(
        user_message=UTTER_DURATION,
        session=session,
        llm=llm,
    )
    assert _tool_names(duration) == ["referent.get_duration"]
    minutes = duration.tool_results[0].data.get("estimated_minutes")
    assert minutes is not None
    assert duration.tool_results[0].data.get("action_id") == alt_items[0]["action"]["id"]
    assert session.context.current_subject_id == alt_id

    fit = run_orchestrator_turn(
        user_message=UTTER_FIT,
        session=session,
        llm=llm,
    )
    assert _tool_names(fit) == ["availability.check"]
    assert fit.tool_calls[0].arguments.get("duration_minutes") == minutes
    assert session.context.current_subject_id == alt_id


def test_recovery_meant_the_token_thing_corrects_subject() -> None:
    """Enigma explained brunch; user names the token task — subject + explain retarget."""
    session = _tool_session()
    _explain_brunch_wrong_subject(session)
    turn = run_orchestrator_turn(
        user_message=UTTER_RECOVERY,
        session=session,
        llm=ScriptedConversationLLM(),
    )
    assert _tool_names(turn) == ["world.explain"]
    assert turn.tool_calls[0].arguments.get("target") == TASK_TOKEN_AUDIT
    assert session.context.current_subject_id == TASK_TOKEN_AUDIT
    explained = [item for item in turn.turn_items if item["kind"] == "attention_item"]
    assert explained
    assert explained[0]["item"]["id"] == TASK_TOKEN_AUDIT
    assert turn.tool_results[0].data.get("subject_id") == TASK_TOKEN_AUDIT


def test_empty_propose_with_brunch_focus_does_not_execute_named_tokens_as_brunch() -> None:
    """Named lexical help retargets TOKEN; {} must not blindly use BRUNCH focus."""
    session = _tool_session()
    session.context.current_subject_id = BRUNCH_ID
    session.context.current_attention_item_id = BRUNCH_ID
    session.context.current_subject_kind = "attention_item"
    session.user_message = "Can you help me do the design tokens"
    result = execute_tool(session, "assist.propose", {})
    assert result.ok
    plans = list(session.pending_assists.values())
    assert plans
    assert plans[0].source_item_id == TASK_TOKEN_AUDIT
    assert plans[0].source_item_id != BRUNCH_ID
    assert result.data.get("target_id") == TASK_TOKEN_AUDIT
    assert session.context.current_subject_id == TASK_TOKEN_AUDIT


def test_named_design_tokens_propose_empty_args_is_audited_in_trace() -> None:
    session = _tool_session()
    session.context.current_subject_id = BRUNCH_ID
    session.context.current_attention_item_id = BRUNCH_ID
    session.context.current_subject_kind = "attention_item"
    utterance = "Can you help me do the design tokens"
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=ScriptedConversationLLM({utterance: [ToolCallRecord(name="assist.propose")]}),
    )
    assert _tool_names(turn) == ["assist.propose"]
    assert turn.tool_calls[0].arguments == {}
    trace = turn.llm_trace
    assert trace is not None
    assert trace.model_tool_request[0]["arguments"] == {}
    assert trace.referent_resolution
    resolution = trace.referent_resolution[0]
    assert resolution["source"] == "named_referent"
    assert resolution["bound_id"] == TASK_TOKEN_AUDIT
    assert TASK_TOKEN_AUDIT in resolution["summary"]
    executed = trace.executed_tool_request[0]
    assert executed["name"] == "assist.propose"
    assert executed["arguments"]["target_id"] == TASK_TOKEN_AUDIT
    plans = list(session.pending_assists.values())
    assert plans[0].source_item_id == TASK_TOKEN_AUDIT


def test_implicit_current_subject_propose_is_visible_in_executed_request() -> None:
    session = _tool_session()
    _seed_token_next_action(session)
    utterance = "Can you help me do that?"
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=ScriptedConversationLLM({utterance: [ToolCallRecord(name="assist.propose")]}),
    )
    trace = turn.llm_trace
    assert trace is not None
    assert turn.tool_calls[0].arguments == {}
    assert trace.model_tool_request[0]["arguments"] == {}
    assert trace.referent_resolution[0]["source"] == "implicit current_subject"
    assert trace.referent_resolution[0]["bound_id"] == TASK_TOKEN_AUDIT
    assert trace.executed_tool_request[0]["arguments"]["target_id"] == TASK_TOKEN_AUDIT
    plans = list(session.pending_assists.values())
    assert plans[0].source_item_id == TASK_TOKEN_AUDIT


def test_approve_without_proposal_id_binds_from_context_and_traces_id() -> None:
    session = _tool_session()
    _seed_token_next_action(session)
    llm = ScriptedConversationLLM(
        {
            "Can you help me do that?": [ToolCallRecord(name="assist.propose")],
            "Go on then.": [ToolCallRecord(name="assist.approve")],
        }
    )
    run_orchestrator_turn(user_message="Can you help me do that?", session=session, llm=llm)
    proposal_id = session.context.current_assist_proposal_id
    assert proposal_id
    approve = run_orchestrator_turn(user_message="Go on then.", session=session, llm=llm)
    assert approve.tool_calls[0].arguments == {}
    trace = approve.llm_trace
    assert trace is not None
    assert trace.model_tool_request[0]["arguments"] == {}
    assert trace.referent_resolution[0]["source"] == "implicit current_assist_proposal_id"
    assert trace.referent_resolution[0]["bound_id"] == proposal_id
    assert trace.executed_tool_request[0]["arguments"]["proposal_id"] == proposal_id
    assert approve.tool_results[0].ok
    assert approve.tool_results[0].data.get("proposal_id") == proposal_id


def test_approve_without_proposal_id_fails_when_none_pending() -> None:
    session = _tool_session()
    utterance = "Go on then."
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=ScriptedConversationLLM({utterance: [ToolCallRecord(name="assist.approve")]}),
    )
    assert turn.tool_results
    assert not turn.tool_results[0].ok
    trace = turn.llm_trace
    assert trace is not None
    assert trace.referent_resolution[0]["source"] == "unresolved"
    assert not (trace.executed_tool_request[0].get("arguments") or {}).get("proposal_id")


def test_demo_llm_path_enabled_when_provider_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from personal_enigma.api.demo_orchestrator import demo_llm_conversation_enabled

    monkeypatch.delenv("ENIGMA_DEMO_LLM_CONVERSATION", raising=False)
    monkeypatch.delenv("LLM_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-test")
    monkeypatch.setenv("ENIGMA_C09_LIVE", "1")
    assert demo_llm_conversation_enabled() is True


def test_demo_llm_path_off_without_key_or_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from personal_enigma.api.demo_orchestrator import demo_llm_conversation_enabled

    monkeypatch.delenv("ENIGMA_DEMO_LLM_CONVERSATION", raising=False)
    monkeypatch.delenv("LLM_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    assert demo_llm_conversation_enabled() is False


def _assert_live_nasty_chain(session: DemoToolSession, llm: EgressConversationLLM) -> None:
    start = run_orchestrator_turn(
        user_message=UTTER_ASSIST,
        session=session,
        llm=llm,
    )
    assert start.tool_calls, "live model returned no tool calls (oracle fallback disabled)"
    _require_tool(start, "assist.propose")
    plans = list(session.pending_assists.values())
    assert plans, "assist.propose did not record a plan"
    assert plans[0].source_item_id == TASK_TOKEN_AUDIT
    assert session.context.current_subject_id == TASK_TOKEN_AUDIT

    why = run_orchestrator_turn(
        user_message=UTTER_EXPLAIN,
        session=session,
        llm=llm,
    )
    _require_tool(why, "world.explain")
    assert why.tool_results[0].data.get("subject_id") == TASK_TOKEN_AUDIT
    assert session.context.current_subject_id == TASK_TOKEN_AUDIT

    reject_alt = run_orchestrator_turn(
        user_message=UTTER_ALTERNATIVE,
        session=session,
        llm=llm,
    )
    names = _tool_names(reject_alt)
    assert "next_action.reject" in names
    assert "next_action.get_alternatives" in names
    alt_items = [item for item in reject_alt.turn_items if item["kind"] == "next_action"]
    assert alt_items, f"expected alternate next_action, tools={names}"
    alt_id = alt_items[0]["action"]["source_candidate_id"]
    assert alt_id != TASK_TOKEN_AUDIT
    assert session.context.current_subject_id == alt_id

    duration = run_orchestrator_turn(
        user_message=UTTER_DURATION,
        session=session,
        llm=llm,
    )
    _require_tool(duration, "referent.get_duration")
    minutes = duration.tool_results[0].data.get("estimated_minutes")
    assert minutes is not None
    assert duration.tool_results[0].data.get("action_id") == alt_items[0]["action"]["id"]
    assert session.context.current_subject_id == alt_id

    fit = run_orchestrator_turn(
        user_message=UTTER_FIT,
        session=session,
        llm=llm,
    )
    check = _require_tool(fit, "availability.check")
    assert check.arguments.get("duration_minutes") == minutes
    assert session.context.current_subject_id == alt_id


def _assert_live_recovery(session: DemoToolSession, llm: EgressConversationLLM) -> None:
    correction = run_orchestrator_turn(
        user_message=UTTER_RECOVERY,
        session=session,
        llm=llm,
    )
    assert correction.tool_calls, "live model returned no tool calls for recovery"
    explain = _require_tool(correction, "world.explain")
    assert explain.arguments.get("target") == TASK_TOKEN_AUDIT
    assert session.context.current_subject_id == TASK_TOKEN_AUDIT
    assert correction.tool_results[0].data.get("subject_id") == TASK_TOKEN_AUDIT


def _assert_live_unsupported(session: DemoToolSession, llm: EgressConversationLLM) -> None:
    turn = run_orchestrator_turn(
        user_message=UTTER_UNSUPPORTED,
        session=session,
        llm=llm,
    )
    assert turn.tool_calls == [], (
        f"unsupported question must not invent tools, got {_tool_names(turn)}"
    )


@pytest.mark.skipif(
    not _c09_live_enabled(),
    reason="Live C09 paraphrase proof requires ENIGMA_C09_LIVE=1 and FIREWORKS_API_KEY",
)
def test_c09_live_fireworks_paraphrase() -> None:
    """Actual model proof — Fireworks via audited egress, no oracle fallback.

    Repeats the off-script chain 3–5 times. Any tool/args/subject mismatch fails
    the run. Graduation stays unmet until this passes.
    """
    llm = EgressConversationLLM(provider="fireworks", fallback_to_oracle=False)
    reps = _c09_live_reps()
    for rep in range(reps):
        session = _tool_session()
        _seed_token_next_action(session)
        try:
            _assert_live_nasty_chain(session, llm)
        except AssertionError as exc:
            raise AssertionError(f"nasty chain failed on rep {rep + 1}/{reps}: {exc}") from exc

        recovery_session = _tool_session()
        _explain_brunch_wrong_subject(recovery_session)
        try:
            _assert_live_recovery(recovery_session, llm)
        except AssertionError as exc:
            raise AssertionError(f"recovery failed on rep {rep + 1}/{reps}: {exc}") from exc

        ignorance_session = _tool_session()
        try:
            _assert_live_unsupported(ignorance_session, llm)
        except AssertionError as exc:
            raise AssertionError(f"unsupported failed on rep {rep + 1}/{reps}: {exc}") from exc
