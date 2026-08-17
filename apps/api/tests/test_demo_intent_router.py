"""Natural-language intent resolution — phrase families, no LLM."""

from __future__ import annotations

from datetime import datetime

import pytest

from personal_enigma.api.demo_availability import format_availability_message
from personal_enigma.api.demo_intents import (
    build_capabilities_turn,
    build_intent_turn,
    build_unsupported_world_turn,
)
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.intent_router import (
    ConversationIntent,
    ConversationIntentKind,
    TimeExpression,
    normalize_utterance,
    resolve_intent,
)

JAN19 = "cp-2026-01-19T10:00"


@pytest.mark.parametrize(
    ("utterance", "kind"),
    [
        ("What needs me?", ConversationIntentKind.ATTENTION_QUERY),
        ("What's urgent?", ConversationIntentKind.ATTENTION_QUERY),
        ("Whats urgent", ConversationIntentKind.ATTENTION_QUERY),
        ("Anything important?", ConversationIntentKind.ATTENTION_QUERY),
        ("Do I need to deal with anything?", ConversationIntentKind.ATTENTION_QUERY),
        ("What should I do next?", ConversationIntentKind.NEXT_ACTION_QUERY),
        ("What's next?", ConversationIntentKind.NEXT_ACTION_QUERY),
        ("What do I need to do now/", ConversationIntentKind.NEXT_ACTION_QUERY),
        ("Give me something to do", ConversationIntentKind.NEXT_ACTION_QUERY),
        ("What should I tackle?", ConversationIntentKind.NEXT_ACTION_QUERY),
        ("Am I free this weekend?", ConversationIntentKind.AVAILABILITY_QUERY),
        ("Can I do Friday night?", ConversationIntentKind.AVAILABILITY_QUERY),
        ("What's Saturday looking like?", ConversationIntentKind.AVAILABILITY_QUERY),
        ("hey", ConversationIntentKind.GREETING),
        ("Hello!", ConversationIntentKind.GREETING),
        ("What changed?", ConversationIntentKind.CHANGES_QUERY),
        ("What am I waiting on?", ConversationIntentKind.WAITING_ON_QUERY),
        ("What can wait?", ConversationIntentKind.CAN_WAIT_QUERY),
        ("Why?", ConversationIntentKind.WHY_QUERY),
        ("Can you help me do that?", ConversationIntentKind.HELP_QUERY),
        ("Where should I book brunch?", ConversationIntentKind.UNKNOWN),
        ("I'm feeling overwhelmed", ConversationIntentKind.UNKNOWN),
        # C05c live-demo regressions (Jan 19)
        ("what should i do now", ConversationIntentKind.NEXT_ACTION_QUERY),
        ("What should i focus on?", ConversationIntentKind.ATTENTION_QUERY),
        ("what is urgent", ConversationIntentKind.ATTENTION_QUERY),
        ("what do i do now", ConversationIntentKind.NEXT_ACTION_QUERY),
        ("what to do now", ConversationIntentKind.NEXT_ACTION_QUERY),
        ("what is important", ConversationIntentKind.ATTENTION_QUERY),
        ("Whats the latest from my emails?", ConversationIntentKind.ATTENTION_QUERY),
        ("double check", ConversationIntentKind.TIME_FIT_QUERY),
        ("Nah, I cant be bothered", ConversationIntentKind.REJECT_NEXT_ACTION),
        # Live-demo regressions — today agenda, urgent typo, casual ack
        ("What do i have on today", ConversationIntentKind.AVAILABILITY_QUERY),
        ("what's on today", ConversationIntentKind.AVAILABILITY_QUERY),
        ("What is ugent?", ConversationIntentKind.ATTENTION_QUERY),
        ("oh no...", ConversationIntentKind.ACKNOWLEDGMENT),
        # Live-demo regressions — weather, capabilities, priorities
        ("Whats the weather like?", ConversationIntentKind.UNSUPPORTED_WORLD_QUERY),
        (
            "Am i just really restricted to conversations?",
            ConversationIntentKind.CAPABILITIES_QUERY,
        ),
        (
            "Whats the top 3 things to get done today",
            ConversationIntentKind.ATTENTION_QUERY,
        ),
        ("What is urgent right now?", ConversationIntentKind.ATTENTION_QUERY),
        ("this week?", ConversationIntentKind.UNKNOWN),
        ("next week?", ConversationIntentKind.UNKNOWN),
        ("this weekend?", ConversationIntentKind.AVAILABILITY_QUERY),
    ],
)
def test_resolve_intent_phrase_families(utterance: str, kind: ConversationIntentKind) -> None:
    assert resolve_intent(utterance).kind == kind


def test_normalize_strips_trailing_slash() -> None:
    assert normalize_utterance("What do I need to do now/") == "what do i need to do now"


def test_normalize_strips_trailing_punctuation() -> None:
    assert normalize_utterance("What should i focus on?") == "what should i focus on"
    assert normalize_utterance("what is urgent.") == "what is urgent"


def test_whats_urgent_without_apostrophe() -> None:
    assert resolve_intent("what is urgent").kind == ConversationIntentKind.ATTENTION_QUERY
    assert resolve_intent("what's urgent").kind == ConversationIntentKind.ATTENTION_QUERY


def test_ugent_typo_repair() -> None:
    assert resolve_intent("What is ugent?").kind == ConversationIntentKind.ATTENTION_QUERY
    assert resolve_intent("what's ugent").kind == ConversationIntentKind.ATTENTION_QUERY


def test_today_agenda_period() -> None:
    resolved = resolve_intent("What do i have on today")
    assert resolved.kind == ConversationIntentKind.AVAILABILITY_QUERY
    assert resolved.period == TimeExpression.TODAY


def test_today_agenda_does_not_match_unrelated() -> None:
    assert resolve_intent("What is the fee today").kind == ConversationIntentKind.UNKNOWN


def test_availability_detects_this_weekend_period() -> None:
    resolved = resolve_intent("Am I free this weekend?")
    assert resolved.kind == ConversationIntentKind.AVAILABILITY_QUERY
    assert resolved.period == TimeExpression.THIS_WEEKEND


@pytest.mark.parametrize(
    ("utterance", "period"),
    [
        ("Am I free later?", TimeExpression.LATER_TODAY),
        ("Am I free this afternoon?", TimeExpression.THIS_AFTERNOON),
        ("Am I free tomorrow?", TimeExpression.TOMORROW),
        ("Am I free this evening?", TimeExpression.THIS_EVENING),
        ("am i fee later", TimeExpression.LATER_TODAY),
    ],
)
def test_relative_availability_periods(utterance: str, period: TimeExpression) -> None:
    resolved = resolve_intent(utterance)
    assert resolved.kind == ConversationIntentKind.AVAILABILITY_QUERY
    assert resolved.period == period


@pytest.mark.parametrize(
    "utterance",
    [
        "What is the fee?",
        "Feel free to do it",
    ],
)
def test_non_availability_phrases_stay_unknown(utterance: str) -> None:
    resolved = resolve_intent(utterance)
    assert resolved.kind != ConversationIntentKind.AVAILABILITY_QUERY


def test_jan19_relative_availability_conservative() -> None:
    state = project_checkpoint(JAN19).state
    reference = datetime.fromisoformat(state.simulated_time)
    for period, phrase in [
        ("later_today", "later today"),
        ("this_afternoon", "this afternoon"),
        ("tomorrow", "tomorrow"),
    ]:
        message = format_availability_message(
            state=state,
            checkpoint_id=JAN19,
            reference=reference,
            period=period,
        )
        assert "don't see anything" in message.lower()
        assert phrase in message.lower()
        assert "completely free" not in message.lower()


def test_jan19_weekend_availability_mentions_brunch() -> None:
    state = project_checkpoint(JAN19).state
    reference = datetime.fromisoformat(state.simulated_time)
    message = format_availability_message(
        state=state,
        checkpoint_id=JAN19,
        reference=reference,
        period="this_weekend",
    )
    lowered = message.lower()
    assert "saturday" in lowered
    assert "brunch" in lowered
    assert "elena" in lowered
    assert "book saturday brunch" in lowered
    assert "sunday" in lowered
    assert "clear" in lowered


def test_weather_returns_honest_ignorance() -> None:
    at = "2026-01-19T10:00:00+00:00"
    turn = build_unsupported_world_turn(at, "Whats the weather like?")
    text = turn[0]["text"].lower()
    assert "weather" in text
    assert "don't" in text or "do not" in text
    assert "not sure i follow" not in text


def test_capabilities_turn_lists_demo_scope() -> None:
    at = "2026-01-19T10:00:00+00:00"
    turn = build_capabilities_turn(at)
    text = turn[0]["text"].lower()
    assert "attention" in text
    assert "next action" in text or "next actions" in text
    assert "calendar" in text
    assert "weather" in text
    assert "not sure i follow" not in text


def test_top_three_priorities_acknowledges_cardinality() -> None:
    state = project_checkpoint(JAN19).state
    turn, _plan = build_intent_turn(
        "Whats the top 3 things to get done today",
        state,
        at=state.simulated_time,
    )
    messages = [item["text"] for item in turn if item["kind"] == "enigma_message"]
    assert messages
    text = " ".join(messages).lower()
    assert "one strong next action" in text
    assert "token" in text
    assert "radar" in text
    assert "brunch" in text
    assert "atlas" in text
    assert "three" in text
    summaries = [item for item in turn if item["kind"] == "attention_summary"]
    assert len(summaries) == 1
    assert len(summaries[0]["state"]["next_actions"]) == 1


def test_compose_this_week_follow_up_after_attention() -> None:
    from personal_enigma.api.intent_router import compose_follow_up_intent

    last = ConversationIntent(kind=ConversationIntentKind.ATTENTION_QUERY)
    resolved = compose_follow_up_intent("this week?", last)
    assert resolved.kind == ConversationIntentKind.ATTENTION_QUERY
    assert resolved.period == TimeExpression.THIS_WEEK


def test_compose_and_after_that_after_this_week() -> None:
    from personal_enigma.api.intent_router import compose_follow_up_intent

    last = ConversationIntent(
        kind=ConversationIntentKind.ATTENTION_QUERY,
        period=TimeExpression.THIS_WEEK,
    )
    resolved = compose_follow_up_intent("and after that?", last)
    assert resolved.kind == ConversationIntentKind.ATTENTION_QUERY
    assert resolved.period == TimeExpression.NEXT_WEEK


def test_compose_next_week_follow_up_after_availability() -> None:
    from personal_enigma.api.intent_router import compose_follow_up_intent

    last = resolve_intent("am i free later")
    assert last.kind == ConversationIntentKind.AVAILABILITY_QUERY
    resolved = compose_follow_up_intent("next week?", last)
    assert resolved.kind == ConversationIntentKind.AVAILABILITY_QUERY
    assert resolved.period == TimeExpression.NEXT_WEEK


def test_this_week_period_only_is_unknown() -> None:
    resolved = resolve_intent("this week?")
    assert resolved.kind == ConversationIntentKind.UNKNOWN
    assert resolve_intent("next week?").kind == ConversationIntentKind.UNKNOWN


def test_jan19_this_week_availability_mentions_brunch() -> None:
    state = project_checkpoint(JAN19).state
    reference = datetime.fromisoformat(state.simulated_time)
    message = format_availability_message(
        state=state,
        checkpoint_id=JAN19,
        reference=reference,
        period="this_week",
    )
    lowered = message.lower()
    assert "this week" in lowered
    assert "saturday" in lowered
    assert "brunch" in lowered
    assert "completely free" not in lowered
