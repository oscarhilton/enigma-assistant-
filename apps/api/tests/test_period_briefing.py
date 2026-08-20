"""BRIEF-01 — period briefing must surface context band, not collapse to silence."""

from __future__ import annotations

from personal_enigma.api.demo_intents import build_attention_horizon_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.intent_router import TimeExpression
from personal_enigma.attention.projection import AttentionState

JAN19 = "cp-2026-01-19T10:00"
JAN20 = "cp-2026-01-20T11:00"


def _state(checkpoint_id: str) -> AttentionState:
    return project_checkpoint(checkpoint_id).state


def test_hows_my_week_resolves_to_attention_this_week() -> None:
    from personal_enigma.api.intent_router import resolve_intent

    resolved = resolve_intent("Hey, how's my week?")
    assert resolved.kind.value == "attention_query"
    assert resolved.period is not None
    assert resolved.period.value == "this_week"


def test_hows_my_week_looking_resolves_to_attention_this_week() -> None:
    from personal_enigma.api.intent_router import resolve_intent

    resolved = resolve_intent("Hey! Hows my week looking?")
    assert resolved.period is not None
    assert resolved.period.value == "this_week"


def test_jan19_week_briefing_mentions_brunch_on_radar_not_interrupt() -> None:
    state = _state(JAN19)
    assert not state.needs_you
    assert any("brunch" in item.title.lower() for item in state.context)
    turn = build_attention_horizon_turn(
        state,
        checkpoint_id=JAN19,
        at=state.simulated_time,
        period=TimeExpression.THIS_WEEK,
    )
    text = turn[0]["text"].lower()
    assert "nothing needs your attention right now" in text
    assert "looking ahead this week" in text
    assert "brunch" in text
    assert "needs you this week as an interrupt" not in text


def test_jan20_week_briefing_surfaces_brunch_as_needs_you() -> None:
    state = _state(JAN20)
    assert state.needs_you
    turn = build_attention_horizon_turn(
        state,
        checkpoint_id=JAN20,
        at=state.simulated_time,
        period=TimeExpression.THIS_WEEK,
    )
    text = turn[0]["text"].lower()
    assert "brunch" in text
    assert "needs you this week" in text


def test_briefing_read_this_week_jan19_via_tool() -> None:
    from personal_enigma.api.conversation_context import ConversationContext
    from personal_enigma.api.demo_tools import DemoToolSession, execute_tool

    state = _state(JAN19)
    session = DemoToolSession(
        state=state,
        context=ConversationContext(),
        checkpoint_id=JAN19,
        prior_state=None,
        at=state.simulated_time,
        conversation=[],
        completed_item_ids=set(),
    )
    result = execute_tool(session, "briefing.read", {"period": "this_week"})
    assert result.ok
    blob = " ".join(str(item.get("text") or "") for item in result.turn_items).lower()
    assert "brunch" in blob
    assert "looking ahead" in blob or "on radar" in blob
