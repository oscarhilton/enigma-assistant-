"""C09 — LLM conversational boundary benchmark (tool layer + orchestrator wiring).

Green here is *harness* proof: tool registry, IntentOracleLLM phrase maps, and
deterministic fallback. Phrase mappings are scaffolding / a test oracle, not
evidence that a remote model can select tools without magic phrases. Together
with the scripted tests in ``test_c09_llm_paraphrase_invariance.py`` this is
architecture around the model (phrase maps = scaffolding). Live Fireworks proof
is separate and skipped without credentials. See that file for orchestration
wiring + live proof.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.api.conversation_context import (
    ConversationContext,
    referent_candidates,
    update_context_from_turn_items,
)
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_orchestrator import (
    EgressConversationLLM,
    IntentOracleLLM,
    context_summary,
    demo_llm_conversation_enabled,
    run_orchestrator_turn,
    set_conversation_llm,
    tool_calls_from_intent,
    trace_path_for_planner,
)
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import DemoToolSession, ToolCallRecord, execute_tool

TOKEN_ID = "item-obligation_token_audit"
ATLAS_ID = "item-obligation_atlas_review"
BRUNCH_ID = "item-obligation_brunch_book"
JAN19 = "cp-2026-01-19T10:00"
JAN20 = "cp-2026-01-20T11:00"


@pytest.fixture
def demo_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.delenv("ENIGMA_DEMO_LLM_CONVERSATION", raising=False)
    monkeypatch.delenv("LLM_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    return TestClient(create_app())


@pytest.fixture
def llm_demo_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.setenv("ENIGMA_DEMO_LLM_CONVERSATION", "1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    return TestClient(create_app())


def _ask(client: TestClient, text: str) -> dict:
    return client.post("/demo/conversation/message", json={"text": text}).json()


def _tool_session(
    checkpoint_id: str = JAN19,
    *,
    context: ConversationContext | None = None,
    prior_checkpoint: str | None = None,
) -> DemoToolSession:
    state = project_checkpoint(checkpoint_id).state
    prior = project_checkpoint(prior_checkpoint).state if prior_checkpoint else None
    return DemoToolSession(
        state=state,
        context=context or ConversationContext(),
        checkpoint_id=checkpoint_id,
        prior_state=prior,
        at=state.simulated_time,
        conversation=[],
        synthetic_services=SyntheticDemoServices(),
    )


@pytest.mark.parametrize(
    "utterance",
    [
        "What's urgent?",
        "Anything urgent?",
        "What should I focus on?",
    ],
)
def test_attention_paraphrases_select_same_tool(utterance: str) -> None:
    calls = tool_calls_from_intent(utterance)
    assert len(calls) == 1
    assert calls[0].name == "attention.get_current"


def test_tool_attention_jan19_preserves_context_not_needs_you() -> None:
    session = _tool_session(JAN19)
    result = execute_tool(session, "attention.get_current", {})
    state = result.data["state"]
    assert state["needs_you"] == []
    context_ids = {row["id"] for row in state["context"]}
    assert TOKEN_ID in context_ids
    assert {item["kind"] for item in result.turn_items} == {"attention_summary"}


def test_tool_next_action_jan19_token_unblocked() -> None:
    session = _tool_session(JAN19)
    result = execute_tool(session, "next_action.get", {})
    assert result.data["next_actions"]
    assert result.data["next_actions"][0]["source_candidate_id"] == TOKEN_ID


def test_tool_reject_and_alternate_retain_referent() -> None:
    session = _tool_session(JAN19)
    ctx = session.context
    next_turn = execute_tool(session, "next_action.get", {})
    action_id = next_turn.data["next_actions"][0]["id"]
    ctx.current_next_action_id = action_id

    reject = execute_tool(session, "next_action.reject", {})
    assert reject.turn_items[0]["kind"] == "enigma_message"
    assert action_id in ctx.suppressed_next_action_ids

    alternate = execute_tool(session, "next_action.get_alternatives", {})
    alt_action = alternate.data["alternate"]
    assert alt_action is not None
    assert alt_action["source_candidate_id"] != TOKEN_ID


def test_tool_duration_from_referent_not_invented() -> None:
    session = _tool_session(JAN19)
    ctx = session.context
    next_turn = execute_tool(session, "next_action.get", {})
    ctx.current_next_action_id = next_turn.data["next_actions"][0]["id"]
    execute_tool(session, "next_action.reject", {})
    alternate = execute_tool(session, "next_action.get_alternatives", {})
    ctx.current_next_action_id = alternate.data["alternate"]["id"]

    duration = execute_tool(session, "referent.get_duration", {})
    assert duration.data["estimated_minutes"] == 15
    assert "15" in duration.turn_items[0]["text"]


def test_tool_availability_weekend_jan19() -> None:
    session = _tool_session(JAN19)
    result = execute_tool(
        session,
        "availability.check",
        {"period": "this_weekend"},
    )
    text = result.turn_items[0]["text"].lower()
    assert "saturday" in text
    assert "brunch" in text


def test_tool_agenda_get_this_week_jan19() -> None:
    session = _tool_session(JAN19)
    result = execute_tool(session, "agenda.get", {"period": "this_week"})
    assert result.ok
    assert result.data["period"] == "this_week"
    evidence = {row["evidence_id"] for row in result.data["calendar_items"]}
    assert "cal-brunch-parents" in evidence
    blob = " ".join(
        str(item.get("text") or "") for item in result.turn_items
    ).lower()
    assert "calendar" in blob
    assert "brunch" in blob
    assert "venue" not in blob
    assert "guest list" not in blob
    assert "best tackled" not in blob
    assert "finish mid-week" not in blob


def test_referent_candidates_are_thin_ids_for_resolution_only() -> None:
    state = project_checkpoint(JAN19).state
    rows = referent_candidates(state)
    assert rows
    assert {row["id"] for row in rows} >= {TOKEN_ID, BRUNCH_ID}
    for row in rows:
        assert set(row) == {"id", "label", "kind"}
        assert row["kind"] in {"attention_item", "next_action"}
        assert "bucket" not in row
        assert "title" not in row
    summary = context_summary(ConversationContext(), state)
    assert "available_subjects" not in summary
    assert summary["referent_candidates"] == rows


def test_tool_world_changes_after_checkpoint_jump(llm_demo_client: TestClient) -> None:
    llm_demo_client.post(f"/demo/timeline/checkpoint/{JAN20}")
    turn = _ask(llm_demo_client, "What changed?")
    assert turn["items"]
    kinds = {item["kind"] for item in turn["items"]}
    assert "attention_item" in kinds or "next_action" in kinds


def test_demo_llm_conversation_enabled_when_provider_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENIGMA_DEMO_LLM_CONVERSATION", raising=False)
    monkeypatch.delenv("LLM_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-test")
    assert demo_llm_conversation_enabled() is True


def test_demo_llm_conversation_disabled_without_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENIGMA_DEMO_LLM_CONVERSATION", raising=False)
    monkeypatch.delenv("LLM_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    assert demo_llm_conversation_enabled() is False


def test_demo_llm_conversation_explicit_off_wins_over_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-test")
    monkeypatch.setenv("ENIGMA_DEMO_LLM_CONVERSATION", "0")
    assert demo_llm_conversation_enabled() is False


def test_trace_path_follows_planner_provider() -> None:
    fireworks = EgressConversationLLM(provider="fireworks", api_key="fw-test")
    openai = EgressConversationLLM(provider="openai", api_key="sk-test")
    assert trace_path_for_planner(fireworks) == "fireworks"
    assert trace_path_for_planner(openai) == "openai"
    assert trace_path_for_planner(IntentOracleLLM()) == "llm"


def test_orchestrator_keys_unknown_no_invention() -> None:
    session = _tool_session(JAN19)
    turn = run_orchestrator_turn(
        user_message="Where did I leave my keys?",
        session=session,
        llm=IntentOracleLLM(),
    )
    assert turn.tool_calls == []
    assert turn.turn_items[0]["text"] == "I don't know."


def test_orchestrator_messy_dialogue_benchmark(llm_demo_client: TestClient) -> None:
    """Sequential messy dialogue — tools + referent retention."""
    assert llm_demo_client.get("/demo/status").json()["checkpoint_id"] == JAN19

    urgent = _ask(llm_demo_client, "What's urgent?")
    summary = urgent["items"][0]["state"]
    assert summary["needs_you"] == []
    assert TOKEN_ID in {row["id"] for row in summary["context"]}

    now = _ask(llm_demo_client, "What should I do right now?")
    assert now["items"][0]["action"]["source_candidate_id"] == TOKEN_ID

    reject = _ask(llm_demo_client, "Nah, I can't be bothered.")
    assert reject["items"][0]["kind"] == "enigma_message"

    alt = _ask(llm_demo_client, "Another task?")
    assert alt["items"][0]["action"]["source_candidate_id"] != TOKEN_ID

    duration = _ask(llm_demo_client, "How long will that take?")
    assert "15" in duration["items"][0]["text"]

    fit = _ask(llm_demo_client, "Do I have time?")
    fit_text = fit["items"][0]["text"].lower()
    assert "minute" in fit_text

    loaded = _ask(llm_demo_client, "What changed?")
    assert "nothing has changed" in loaded["items"][0]["text"].lower()

    weekend = _ask(llm_demo_client, "Am I free this weekend?")
    assert "brunch" in weekend["items"][0]["text"].lower()

    keys = _ask(llm_demo_client, "Where did I leave my keys?")
    assert keys["items"][0]["text"] == "I don't know."


def test_llm_path_matches_intent_router_attention_paraphrase(
    demo_client: TestClient,
    llm_demo_client: TestClient,
) -> None:
    router_turn = _ask(demo_client, "What needs me?")
    llm_turn = _ask(llm_demo_client, "Anything urgent?")
    router_ctx = {row["id"] for row in router_turn["items"][0]["state"]["context"]}
    llm_ctx = {row["id"] for row in llm_turn["items"][0]["state"]["context"]}
    assert router_ctx == llm_ctx


def test_jan19_projection_unchanged_with_llm_disabled(demo_client: TestClient) -> None:
    """Jan 19 regression: token in context, never promoted to needs_you."""
    state = demo_client.get("/demo/attention/state").json()
    assert state["needs_you"] == []
    assert TOKEN_ID in {row["id"] for row in state["context"]}


def test_jan19_projection_unchanged_with_llm_enabled(llm_demo_client: TestClient) -> None:
    state = llm_demo_client.get("/demo/attention/state").json()
    assert state["needs_you"] == []
    assert TOKEN_ID in {row["id"] for row in state["context"]}


def test_assist_propose_never_auto_executes(llm_demo_client: TestClient) -> None:
    _ask(llm_demo_client, "What should I do right now?")
    turn = _ask(llm_demo_client, "Can you help me do that?")
    assert turn["items"][0]["kind"] == "assist_proposal"
    assert "proposal" in turn["items"][0]


def test_subject_referent_tool_mappings() -> None:
    """Orchestrator-only phrase → tool (intent_router not expanded)."""
    assert tool_calls_from_intent("lets start todays action") == [
        ToolCallRecord(name="assist.propose")
    ]
    assert tool_calls_from_intent("Why do i need to do this?") == [
        ToolCallRecord(name="world.explain")
    ]
    assert tool_calls_from_intent("thats a completely different task") == [
        ToolCallRecord(name="world.explain", arguments={"recover": True})
    ]
    assert tool_calls_from_intent("Anything else?") == [
        ToolCallRecord(name="next_action.get_alternatives")
    ]


def test_subject_referent_acceptance_transcript(llm_demo_client: TestClient) -> None:
    """C09 acceptance: top-3 → assist → explain → reject → alt → duration → time-fit."""
    top = _ask(llm_demo_client, "Whats the top 3 things to get done today")
    summaries = [item for item in top["items"] if item["kind"] == "attention_summary"]
    assert len(summaries) == 1
    assert len(summaries[0]["state"]["next_actions"]) == 1
    assert summaries[0]["state"]["next_actions"][0]["source_candidate_id"] == TOKEN_ID
    messages = [
        item["text"] for item in top["items"] if item["kind"] == "enigma_message"
    ]
    assert any("one strong next action" in text.lower() for text in messages)

    start = _ask(llm_demo_client, "lets start todays action")
    assert start["items"][0]["kind"] == "assist_proposal"
    assert "token" in start["items"][0]["proposal"]["title"].lower()

    why = _ask(llm_demo_client, "Why do i need to do this?")
    why_items = [item for item in why["items"] if item["kind"] == "attention_item"]
    assert why_items
    assert why_items[0]["item"]["id"] == TOKEN_ID
    assert why_items[0]["item"]["id"] != BRUNCH_ID

    reject = _ask(llm_demo_client, "Actually, I can't be bothered.")
    assert reject["items"][0]["kind"] == "enigma_message"

    alt = _ask(llm_demo_client, "Anything else?")
    assert alt["items"][0]["kind"] == "next_action"
    assert alt["items"][0]["action"]["source_candidate_id"] != TOKEN_ID

    duration = _ask(llm_demo_client, "How long will that take?")
    assert "15" in duration["items"][0]["text"]

    fit = _ask(llm_demo_client, "Do I have time?")
    assert "minute" in fit["items"][0]["text"].lower()


def test_subject_referent_wrong_referent_recovery(llm_demo_client: TestClient) -> None:
    """User corrects wrong subject — orchestrator recovers via world.explain(recover=true)."""
    _ask(llm_demo_client, "Whats the top 3 things to get done today")
    correction = _ask(llm_demo_client, "thats a completely different task")
    assert correction["items"][0]["kind"] == "enigma_message"
    assert "switched tasks" in correction["items"][0]["text"].lower()
    assert correction["items"][1]["kind"] == "attention_item"
    assert correction["items"][1]["item"]["id"] == TOKEN_ID


def _assert_trace_has_no_raw_email(trace: dict) -> None:
    blob = json.dumps(
        {
            "remote_context_sent": trace.get("remote_context_sent"),
            "disclosure": trace.get("disclosure"),
            "tool_results": trace.get("tool_results"),
            "included": trace.get("included"),
            "excluded": trace.get("excluded"),
        },
        default=str,
    )
    assert "@" not in blob


def test_router_path_message_includes_llm_trace(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "What should I do next?")
    trace = turn["llm_trace"]
    assert turn["debug"] == trace
    assert trace["path"] == "intent_router"
    assert trace["planner"] == "intent_router"
    assert trace["intent_name"] == "next_action_query"
    assert trace["user_message"] == "What should I do next?"
    assert trace["remote_context_sent"] is None
    assert trace["model_tool_request"] == []
    assert trace["router_fallback"] is True
    assert "PRIVATE_RAW" in trace["excluded"]
    assert "raw email bodies" in trace["excluded"]
    assert turn["items"][0]["llm_trace"]["path"] == "intent_router"
    _assert_trace_has_no_raw_email(trace)


def test_llm_path_message_includes_tool_trace(llm_demo_client: TestClient) -> None:
    turn = _ask(llm_demo_client, "What should I do next?")
    trace = turn["llm_trace"]
    assert trace["path"] == "llm"
    assert trace["planner"] == "IntentOracleLLM"
    assert trace["intent_name"] == "next_action_query"
    assert trace["remote_context_sent"] is None
    names = [row["name"] for row in trace["model_tool_request"]]
    assert "next_action.get" in names
    assert trace["tool_results"]
    assert trace["tool_results"][0]["name"] == "next_action.get"
    assert "next_action.get" in trace["tools_available"]
    assert "current_subject_id" in trace["conversation_state"]
    _assert_trace_has_no_raw_email(trace)


class _ScriptedFrontDoorLLM:
    """Test double for the live front door — not a production phrase map."""

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
        if user_message not in self._script:
            raise AssertionError(f"unscripted utterance: {user_message!r}")
        return [call.model_copy(deep=True) for call in self._script[user_message]]


def test_demo_session_exposes_chat_index_for_llm_front_door() -> None:
    """Live Demo LLM path reads DemoSession.chat_index; missing attr is HTTP 500."""
    from personal_enigma.api.demo_chat import DemoChatIndex
    from personal_enigma.api.routes.demo import DemoSession

    session = DemoSession()
    assert isinstance(session.chat_index, DemoChatIndex)


def test_front_door_enters_orchestrator_when_fireworks_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /demo/conversation/message must not take intent_router when a key exists."""
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-test")
    monkeypatch.delenv("ENIGMA_DEMO_LLM_CONVERSATION", raising=False)
    monkeypatch.delenv("LLM_DISABLED", raising=False)
    scripted = _ScriptedFrontDoorLLM(
        {
            "Anything important in my emails?": [
                ToolCallRecord(name="attention.get_current")
            ],
            "Hey! Hows my week looking?": [
                ToolCallRecord(name="agenda.get", arguments={"period": "this_week"})
            ],
        }
    )
    set_conversation_llm(scripted)
    try:
        client = TestClient(create_app())
        emails = _ask(client, "Anything important in my emails?")
        email_trace = emails["llm_trace"]
        assert email_trace["path"] != "intent_router"
        assert email_trace["router_fallback"] is False
        assert email_trace["user_message"] == "Anything important in my emails?"
        assert [row["name"] for row in email_trace["model_tool_request"]] == [
            "attention.get_current"
        ]
        assert "gmail.search" not in [row["name"] for row in email_trace["model_tool_request"]]
        first = emails["items"][0]
        assert first["kind"] == "attention_summary"
        assert first.get("text")
        assert first["text"] != "attention_summary"

        week = _ask(client, "Hey! Hows my week looking?")
        week_trace = week["llm_trace"]
        assert week_trace["path"] != "intent_router"
        names = [row["name"] for row in week_trace["model_tool_request"]]
        assert names == ["agenda.get"]
        assert week_trace["model_tool_request"][0]["arguments"].get("period") == "this_week"
        assert week["items"][0].get("text") != "I'm not sure I follow."
    finally:
        set_conversation_llm(None)


def test_attention_summary_text_is_not_kind_name() -> None:
    session = _tool_session(JAN19)
    result = execute_tool(session, "attention.get_current", {})
    item = result.turn_items[0]
    assert item["kind"] == "attention_summary"
    assert item.get("text")
    assert item["text"] != item["kind"]
    assert "needs you" in item["text"].lower()


def test_disabled_llm_keeps_honest_router_fallback(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "Hey! Hows my week looking?")
    trace = turn["llm_trace"]
    assert trace["path"] == "intent_router"
    assert trace["router_fallback"] is True
    assert trace["remote_context_sent"] is None
    assert turn["items"][0]["text"] == "I'm not sure I follow."


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


def test_empty_agenda_does_not_set_subject_from_referent_candidates() -> None:
    """A leftover candidate may stay resolvable without becoming focus."""
    session = _tool_session(JAN19)
    ids = {row["id"] for row in referent_candidates(session.state)}
    assert BRUNCH_ID in ids
    assert session.context.current_subject_id is None
    utterance = "What's on next week?"
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM(
            {
                utterance: [
                    ToolCallRecord(name="agenda.get", arguments={"period": "next_week"})
                ]
            }
        ),
    )
    assert turn.tool_results[0].data.get("empty_horizon") is True
    kinds = {item["kind"] for item in turn.turn_items}
    assert "attention_item" not in kinds
    assert "next_action" not in kinds
    assert session.context.current_subject_id is None
    assert session.context.focus_reason == "empty_horizon"
    assert BRUNCH_ID in {row["id"] for row in referent_candidates(session.state)}


def test_leftover_radar_card_does_not_become_current_subject() -> None:
    ctx = ConversationContext()
    update_context_from_turn_items(
        ctx,
        [
            {
                "kind": "enigma_message",
                "text": "I don't see anything on the calendar next week.",
            },
            {
                "kind": "attention_item",
                "item": {"id": BRUNCH_ID, "title": "Book brunch with Elena's parents"},
            },
        ],
    )
    assert ctx.current_subject_id is None


def test_horizon_radar_does_not_steal_token_focus() -> None:
    ctx = ConversationContext(
        current_subject_id=TOKEN_ID,
        current_subject_kind="next_action",
        focus_reason="primary_answer",
    )
    update_context_from_turn_items(
        ctx,
        [
            {
                "kind": "next_action",
                "action": {
                    "id": "next-item-obligation_token_audit",
                    "source_candidate_id": TOKEN_ID,
                    "title": "Draft colour + spacing token inventory",
                },
            },
            {
                "kind": "attention_item",
                "item": {"id": BRUNCH_ID, "title": "Book brunch with Elena's parents"},
            },
        ],
    )
    assert ctx.current_subject_id == TOKEN_ID


def test_when_should_i_continues_from_duration_to_availability() -> None:
    """Duration is an intermediate fact. C09 continues until 'when' is answered."""
    session = _tool_session(JAN19)
    session.context.current_subject_id = BRUNCH_ID
    session.context.current_attention_item_id = BRUNCH_ID
    session.context.temporal_constraint = "saturday"
    utterance = "When should I do it?"
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="referent.get_duration")]}),
    )
    names = [result.name for result in turn.tool_results]
    assert names == ["referent.get_duration", "availability.check"]
    assert turn.tool_results[1].data.get("task_minutes") == 15
    assert turn.tool_results[1].data.get("period") == "saturday"


def test_like_now_continues_from_duration_to_current_availability() -> None:
    session = _tool_session(JAN19)
    session.context.current_subject_id = BRUNCH_ID
    session.context.current_attention_item_id = BRUNCH_ID
    utterance = "Like... now?"
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="referent.get_duration")]}),
    )
    names = [result.name for result in turn.tool_results]
    assert names == ["referent.get_duration", "availability.check"]
    assert turn.tool_results[1].data.get("period") is None
    assert turn.tool_results[1].data.get("task_minutes") == 15


def test_how_long_does_not_compose_availability() -> None:
    session = _tool_session(JAN19)
    session.context.current_subject_id = BRUNCH_ID
    session.context.current_attention_item_id = BRUNCH_ID
    utterance = "How long will that take?"
    turn = run_orchestrator_turn(
        user_message=utterance,
        session=session,
        llm=_ScriptedLLM({utterance: [ToolCallRecord(name="referent.get_duration")]}),
    )
    assert [result.name for result in turn.tool_results] == ["referent.get_duration"]


def test_context_summary_keeps_oracle_intent_and_exposes_temporal_constraint() -> None:
    from personal_enigma.api.intent_router import (
        ConversationIntent,
        ConversationIntentKind,
        TimeExpression,
    )

    ctx = ConversationContext(
        current_subject_id=TOKEN_ID,
        temporal_constraint="saturday",
        last_intent=ConversationIntent(
            kind=ConversationIntentKind.AVAILABILITY_QUERY,
            period=TimeExpression.SATURDAY,
        ),
    )
    summary = context_summary(ctx)
    assert summary["temporal_constraint"] == "saturday"
    assert summary["last_intent_kind"] == "availability_query"
    assert summary["last_period"] == "saturday"


def test_remote_conversation_payload_omits_stale_classifier_label() -> None:
    from personal_enigma.privacy.egress.classification import RemoteSafeContext

    remote = RemoteSafeContext.for_conversation_orchestrator(
        user_message="When should I do it?",
        context_summary={
            "current_subject_id": BRUNCH_ID,
            "last_intent_kind": "availability_query",
            "last_period": "saturday",
            "temporal_constraint": "saturday",
            "pending_dialogue_act": None,
        },
        tools=[],
        model="accounts/fireworks/models/gpt-oss-120b",
        provider="fireworks",
    )
    user_content = json.loads(remote.wire_body["messages"][1]["content"])
    conversation = user_content["conversation"]
    assert "last_intent_kind" not in conversation
    assert "last_period" not in conversation
    assert conversation["temporal_constraint"] == "saturday"

