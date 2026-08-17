"""C05d conversational continuity — session referents + compositional follow-ups."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from personal_enigma.api import create_app
from personal_enigma.api.intent_router import ConversationIntentKind, resolve_intent

TOKEN_ID = "item-obligation_token_audit"
ATLAS_ID = "item-obligation_atlas_review"
BRUNCH_ID = "item-obligation_brunch_book"
JAN19 = "cp-2026-01-19T10:00"


@pytest.fixture
def demo_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.delenv("ENIGMA_DEMO_LLM_CONVERSATION", raising=False)
    monkeypatch.delenv("LLM_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    return TestClient(create_app())


def _ask(client: TestClient, text: str) -> dict:
    return client.post("/demo/conversation/message", json={"text": text}).json()


@pytest.mark.parametrize(
    "utterance",
    [
        "What should I do right now?",
        "what should i do right now",
    ],
)
def test_right_now_alias_is_next_action(utterance: str) -> None:
    assert resolve_intent(utterance).kind == ConversationIntentKind.NEXT_ACTION_QUERY


@pytest.mark.parametrize(
    ("utterance", "kind"),
    [
        ("Nah, I can't be bothered.", ConversationIntentKind.REJECT_NEXT_ACTION),
        ("can't be bothered", ConversationIntentKind.REJECT_NEXT_ACTION),
        ("Another task I can do?", ConversationIntentKind.ALTERNATE_TASK_QUERY),
        ("another task", ConversationIntentKind.ALTERNATE_TASK_QUERY),
        ("How much time would it take?", ConversationIntentKind.DURATION_QUERY),
        ("how much time", ConversationIntentKind.DURATION_QUERY),
        ("Do I have time?", ConversationIntentKind.TIME_FIT_QUERY),
    ],
)
def test_c05d_intent_kinds(utterance: str, kind: ConversationIntentKind) -> None:
    assert resolve_intent(utterance).kind == kind


def test_jan19_continuity_acceptance_script(demo_client: TestClient) -> None:
    """Five-turn script: next → reject → alternate → duration → time fit."""
    assert demo_client.get("/demo/status").json()["checkpoint_id"] == JAN19

    # 1. What should I do right now? → token next_action
    turn1 = _ask(demo_client, "What should I do right now?")
    assert {item["kind"] for item in turn1["items"]} == {"next_action"}
    action1 = turn1["items"][0]["action"]
    assert action1["source_candidate_id"] == TOKEN_ID

    # 2. Nah, I can't be bothered. → acknowledge; token suppressed for cycle
    turn2 = _ask(demo_client, "Nah, I can't be bothered.")
    assert {item["kind"] for item in turn2["items"]} == {"enigma_message"}
    assert turn2["items"][0]["text"] in {"Fair enough.", "Sure."}
    # World state unchanged — next_action query still surfaces token
    turn2b = _ask(demo_client, "What should I do right now?")
    assert turn2b["items"][0]["action"]["source_candidate_id"] == TOKEN_ID

    # 3. Another task I can do? → alternate (not token)
    turn3 = _ask(demo_client, "Another task I can do?")
    assert {item["kind"] for item in turn3["items"]} == {"next_action"}
    alternate = turn3["items"][0]["action"]
    assert alternate["source_candidate_id"] != TOKEN_ID
    assert alternate["source_candidate_id"] in {ATLAS_ID, BRUNCH_ID}

    # 4. How much time would it take? → duration of alternate
    turn4 = _ask(demo_client, "How much time would it take?")
    assert {item["kind"] for item in turn4["items"]} == {"enigma_message"}
    duration_text = turn4["items"][0]["text"].lower()
    assert "minute" in duration_text
    assert "15" in duration_text

    # 5. Do I have time? → duration + availability composition
    turn5 = _ask(demo_client, "Do I have time?")
    assert {item["kind"] for item in turn5["items"]} == {"enigma_message"}
    fit_text = turn5["items"][0]["text"].lower()
    assert "minute" in fit_text
    assert "don't see anything blocking" in fit_text or "free before" in fit_text
    assert "completely free" not in fit_text


def test_reject_does_not_mutate_attention_state(demo_client: TestClient) -> None:
    before = demo_client.get("/demo/attention/state").json()
    _ask(demo_client, "What should I do right now?")
    _ask(demo_client, "Nah, I can't be bothered.")
    after = demo_client.get("/demo/attention/state").json()
    assert after["next_actions"] == before["next_actions"]
    assert after["context"] == before["context"]


def test_duration_without_referent(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "How much time would it take?")
    assert turn["items"][0]["text"] == "I'm not sure what you're referring to."


def test_unknown_location_deferred(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "Where did I leave my keys?")
    assert turn["items"][0]["text"] == "I don't know."


def test_no_provider_without_llm_flag_uses_intent_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No-key CI path stays on the frozen router."""
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.delenv("ENIGMA_DEMO_LLM_CONVERSATION", raising=False)
    monkeypatch.delenv("LLM_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    client = TestClient(create_app())

    turn = _ask(client, "What should I do right now?")
    assert {item["kind"] for item in turn["items"]} == {"next_action"}
    assert turn["items"][0]["action"]["source_candidate_id"] == TOKEN_ID
    assert turn["llm_trace"]["path"] == "intent_router"


@pytest.mark.parametrize(
    "utterance",
    [
        "Whats the latest from my emails?",
        "What should I do right now?",
        "Nah, I cant be bothered",
        "Another task i can do?",
        "What do i have on today",
        "What is ugent?",
        "oh no...",
        "this weekend?",
    ],
)
def test_jan19_live_demo_regressions(demo_client: TestClient, utterance: str) -> None:
    """Utterances that failed in live demo must not fall through to 'I'm not sure I follow.'"""
    if utterance == "Another task i can do?":
        _ask(demo_client, "What should I do right now?")
        _ask(demo_client, "Nah, I cant be bothered")

    turn = _ask(demo_client, utterance)
    assert turn["items"]
    first = turn["items"][0]
    if first.get("kind") == "enigma_message":
        assert first["text"] != "I'm not sure I follow."
    else:
        assert first["kind"] in {"attention_summary", "next_action"}


def test_today_agenda_returns_calendar_message(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "What do i have on today")
    assert turn["items"][0]["kind"] == "enigma_message"
    assert "calendar" in turn["items"][0]["text"].lower()


def test_ugent_typo_returns_attention_summary(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "What is ugent?")
    assert turn["items"][0]["kind"] == "attention_summary"


def test_oh_no_returns_acknowledgment(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "oh no...")
    assert turn["items"][0]["kind"] == "enigma_message"
    assert turn["items"][0]["text"] == "I hear you."


def test_double_check_follow_up_after_time_fit(demo_client: TestClient) -> None:
    _ask(demo_client, "What should I do right now?")
    _ask(demo_client, "Nah, I cant be bothered")
    _ask(demo_client, "Another task i can do?")
    _ask(demo_client, "how much time would it take?")
    _ask(demo_client, "do I have time?")
    turn = _ask(demo_client, "double check")
    assert turn["items"][0]["kind"] == "enigma_message"
    assert turn["items"][0]["text"] != "I'm not sure I follow."
    assert "minute" in turn["items"][0]["text"].lower()


def test_this_week_follow_up_after_attention(demo_client: TestClient) -> None:
    first = _ask(demo_client, "what needs me")
    assert first["items"][0]["kind"] == "attention_summary"
    turn = _ask(demo_client, "this week?")
    text = " ".join(
        item["text"] for item in turn["items"] if item["kind"] == "enigma_message"
    ).lower()
    assert "i'm not sure i follow" not in text
    assert "this week" in text
    assert "brunch" in text
    assert "token" in text
    next_actions = [item for item in turn["items"] if item["kind"] == "next_action"]
    assert len(next_actions) == 1
    assert next_actions[0]["action"]["source_candidate_id"] == TOKEN_ID


def test_this_week_follow_up_after_urgent_right_now(demo_client: TestClient) -> None:
    """Urgent now → 'this week?' reuses attention_query over THIS_WEEK world state."""
    first = _ask(demo_client, "What is urgent right now?")
    assert first["items"][0]["kind"] == "attention_summary"
    turn = _ask(demo_client, "this week?")
    text = " ".join(
        item["text"] for item in turn["items"] if item["kind"] == "enigma_message"
    ).lower()
    assert "i'm not sure i follow" not in text
    assert "this week" in text
    assert "brunch" in text or "saturday" in text
    assert "token" in text
    assert "interrupt" in text
    next_actions = [item for item in turn["items"] if item["kind"] == "next_action"]
    assert len(next_actions) == 1
    assert next_actions[0]["action"]["source_candidate_id"] == TOKEN_ID
    # Atlas has no week-bounded evidence — do not copy the previous radar list.
    atlas_items = [
        item
        for item in turn["items"]
        if item["kind"] == "attention_item" and item["item"]["id"] == ATLAS_ID
    ]
    assert atlas_items == []


def test_this_week_without_prior_intent_is_unknown(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "this week?")
    assert turn["items"][0]["kind"] == "enigma_message"
    assert turn["items"][0]["text"] == "I'm not sure I follow."


def test_tomorrow_follow_up_after_urgent(demo_client: TestClient) -> None:
    _ask(demo_client, "What is urgent right now?")
    turn = _ask(demo_client, "tomorrow?")
    text = turn["items"][0]["text"].lower()
    assert "i'm not sure i follow" not in text
    assert "tomorrow" in text
    next_actions = [item for item in turn["items"] if item["kind"] == "next_action"]
    assert next_actions == []


def test_and_after_that_after_this_week(demo_client: TestClient) -> None:
    _ask(demo_client, "What is urgent right now?")
    _ask(demo_client, "this week?")
    turn = _ask(demo_client, "and after that?")
    text = turn["items"][0]["text"].lower()
    assert "i'm not sure i follow" not in text
    assert "next week" in text


def test_next_week_follow_up_after_am_i_free_later(demo_client: TestClient) -> None:
    first = _ask(demo_client, "am i free later")
    first_text = first["items"][0]["text"].lower()
    assert "i'm not sure i follow" not in first_text
    turn = _ask(demo_client, "next week?")
    text = turn["items"][0]["text"].lower()
    assert "i'm not sure i follow" not in text
    assert "next week" in text


def test_friday_follow_up_stays_outside_fence(demo_client: TestClient) -> None:
    _ask(demo_client, "What is urgent right now?")
    turn = _ask(demo_client, "what about Friday?")
    assert turn["items"][0]["text"] == "I'm not sure I follow."


def test_top_three_priorities_live(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "Whats the top 3 things to get done today")
    messages = [item["text"] for item in turn["items"] if item["kind"] == "enigma_message"]
    assert messages
    text = " ".join(messages).lower()
    assert "one strong next action" in text
    assert "token" in text
    assert "radar" in text
    assert "brunch" in text
    assert "atlas" in text
    assert "three" in text
    summaries = [item for item in turn["items"] if item["kind"] == "attention_summary"]
    assert len(summaries) == 1
    assert len(summaries[0]["state"]["next_actions"]) == 1
    extra_actions = [item for item in turn["items"] if item["kind"] == "next_action"]
    assert extra_actions == []


def test_latest_from_emails_returns_attention_summary(demo_client: TestClient) -> None:
    turn = _ask(demo_client, "Whats the latest from my emails?")
    assert turn["items"][0]["kind"] == "attention_summary"
    assert TOKEN_ID in {row["id"] for row in turn["items"][0]["state"]["context"]}


def test_reconcile_action_focus_clears_stale_next_action_keeps_subject() -> None:
    from personal_enigma.api.conversation_context import (
        ConversationContext,
        reconcile_action_focus,
    )
    from personal_enigma.attention.projection import (
        AttentionItemView,
        AttentionState,
        PresentationPlan,
    )

    ctx = ConversationContext(
        current_subject_id=TOKEN_ID,
        current_next_action_id="next-item-obligation_token_audit",
        current_attention_item_id=TOKEN_ID,
    )
    state = AttentionState(
        simulated_time="2026-01-19T10:00:00+00:00",
        checkpoint_id=JAN19,
        needs_you=[],
        context=[
            AttentionItemView(
                id=TOKEN_ID,
                title="Draft colour + spacing token inventory",
                explanation="Unblocked.",
                policy_decision="context",
                bucket="context",
            )
        ],
        next_actions=[],
        presentation=PresentationPlan(),
    )
    reconcile_action_focus(ctx, state)
    assert ctx.current_next_action_id is None
    assert ctx.current_subject_id == TOKEN_ID


def test_draft_assist_clears_stale_next_action_keeps_subject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENIGMA_ENVIRONMENT_MODE", "demo")
    monkeypatch.delenv("ENIGMA_DEMO_LLM_CONVERSATION", raising=False)
    monkeypatch.delenv("LLM_DISABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    from personal_enigma.api.routes.demo import DemoSession

    session = DemoSession()
    session.handle_message("What should I do next?")
    assert session.conversation_context.current_subject_id == TOKEN_ID
    assert session.conversation_context.current_next_action_id == (
        "next-item-obligation_token_audit"
    )
    propose = session.handle_message("Help me do this")
    proposal_id = propose["items"][0]["proposal"]["id"]
    session.approve_assist(proposal_id)
    assert TOKEN_ID not in session.completed_item_ids
    assert session.conversation_context.current_subject_id == TOKEN_ID
    assert session.conversation_context.current_next_action_id is None
    live = session._attention_state()
    assert TOKEN_ID in {row.id for row in live.context}
    assert live.next_actions
    assert live.next_actions[0].title.lower() == "review the draft"
    assert BRUNCH_ID in {row.id for row in live.context} or ATLAS_ID in {
        row.id for row in live.context
    }
