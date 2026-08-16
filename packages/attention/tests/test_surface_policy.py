"""Attention surface policy — F-* regression fixtures from D14 wind tunnel."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from personal_enigma.attention import (
    AttentionItem,
    AttentionKind,
    DeadlinePhase,
    HeuristicAttentionEngine,
    classify_deadline,
    collect_attention_items,
    deadline_why_now_glance,
    looks_like_machine_noise,
    looks_like_newsletter,
    looks_like_package_notification,
    partition_surface,
    why_now_glance_for_deadline,
)
from personal_enigma.fixtures import build_calendar_event, build_message, build_reminder

NOW = datetime(2026, 1, 20, 12, 0, tzinfo=UTC)


def test_f_calendar_existence_is_not_attention() -> None:
    """F-calendar-existence-is-not-attention: standup / 1:1 / dentist stay quiet."""
    events = [
        build_calendar_event(
            id="cal-standup",
            title="Team standup",
            start_at=NOW + timedelta(hours=1),
            end_at=NOW + timedelta(hours=1, minutes=15),
        ),
        build_calendar_event(
            id="cal-maya",
            provider_event_id="EK-maya",
            title="1:1 Maya",
            start_at=NOW + timedelta(days=1),
            end_at=NOW + timedelta(days=1, hours=1),
        ),
        build_calendar_event(
            id="cal-dentist",
            provider_event_id="EK-dentist",
            title="Dentist",
            start_at=NOW + timedelta(days=3),
            end_at=NOW + timedelta(days=3, hours=1),
        ),
    ]
    assert collect_attention_items(calendar_events=events, now=NOW) == []


def test_f_past_calendar_event_resolves() -> None:
    """F-past-calendar-event-resolves: Jan 5 standup does not linger overdue."""
    past = build_calendar_event(
        id="cal-jan5-standup",
        title="Team standup",
        start_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
        end_at=datetime(2026, 1, 5, 9, 15, tzinfo=UTC),
    )
    assert (
        collect_attention_items(
            calendar_events=[past],
            now=NOW,
            allow_bare_calendar=True,
        )
        == []
    )
    phase = classify_deadline(past.start_at, now=NOW)
    assert phase is DeadlinePhase.STALE
    assert deadline_why_now_glance(phase) == "Stale — past due"
    assert why_now_glance_for_deadline(past.start_at, now=NOW) == "Stale — past due"


def test_f_automated_mail_is_not_commitment() -> None:
    """F-automated-mail-is-not-commitment: BuildCloud / PrizeVault never commit."""
    messages = [
        build_message(
            id="msg-buildcloud",
            subject="BuildCloud: build #442 failed",
            snippet="Build #442 failed on main.",
            body_text="BuildCloud notifications — build #442 failed.",
            from_person={"display_name": "BuildCloud", "email": "noreply@buildcloud.example"},
        ),
        build_message(
            id="msg-prize",
            subject="PrizeVault: claim your reward",
            snippet="Claim your PrizeVault reward today.",
            body_text="PrizeVault — claim your reward. Unsubscribe below.",
            from_person={"display_name": "PrizeVault", "email": "wins@prizevault.example"},
        ),
    ]
    assert all(looks_like_machine_noise(m) for m in messages)
    assert collect_attention_items(messages=messages) == []


def test_f_newsletter_is_not_commitment() -> None:
    """F-newsletter-is-not-commitment."""
    message = build_message(
        id="msg-design-weekly",
        subject="Design Weekly #214",
        snippet="This week in design systems.",
        body_text="Design Weekly digest. Unsubscribe anytime.",
        from_person={"display_name": "Design Weekly", "email": "news@designledger.example"},
    )
    assert looks_like_newsletter(message)
    assert collect_attention_items(messages=[message]) == []


def test_f_package_notification_is_not_commitment() -> None:
    """F-package-notification-is-not-commitment: RouteFox delivery noise."""
    message = build_message(
        id="msg-routefox",
        subject="RouteFox: your package is out for delivery",
        snippet="Your package is out for delivery.",
        body_text="RouteFox tracking: out for delivery today.",
        from_person={"display_name": "RouteFox", "email": "shipments@routefox.example"},
    )
    assert looks_like_package_notification(message)
    assert collect_attention_items(messages=[message]) == []


def test_f_social_question_is_pending_reply() -> None:
    """F-social-question-is-pending-reply: not INFERRED_COMMITMENT 0.55."""
    message = build_message(
        id="msg-sync",
        subject="Quick sync next week?",
        snippet="Are you free for a quick sync next week?",
        body_text="Hey — quick sync next week?",
        from_person={"display_name": "Maya Chen", "email": "maya@northwind.example"},
    )
    items = collect_attention_items(messages=[message])
    assert len(items) == 1
    assert items[0].kind == AttentionKind.PENDING_REPLY
    assert items[0].priority == 2
    assert items[0].score <= 0.35


def test_f_low_priority_candidate_not_surfaced() -> None:
    """F-low-priority-candidate-not-surfaced: P2 stays candidate, not interrupt."""
    engine = HeuristicAttentionEngine()
    candidates = engine.rank(
        [
            AttentionItem(
                title="Quick sync next week?",
                body="Are you free?",
                kind=AttentionKind.PENDING_REPLY,
                score=0.35,
                priority=2,
            ),
            AttentionItem(
                title="Book Saturday brunch for Elena's parents",
                body=f"Due {(NOW + timedelta(days=2)).isoformat()}",
                kind=AttentionKind.EXPLICIT_REMINDER,
                score=0.98,
                priority=5,
            ),
            AttentionItem(
                title="Draft colour + spacing token inventory",
                body=f"Due {(NOW + timedelta(days=1)).isoformat()}",
                kind=AttentionKind.EXPLICIT_REMINDER,
                score=0.98,
                priority=5,
            ),
        ]
    )
    surfaced, held = partition_surface(candidates, now=NOW)
    titles = {i.title for i in surfaced}
    assert "Book Saturday brunch for Elena's parents" in titles
    assert "Draft colour + spacing token inventory" in titles
    assert "Quick sync next week?" not in titles
    assert any(i.title == "Quick sync next week?" for i in held)
    assert len(surfaced) == 2


def test_deadline_phases_not_approaching_for_past() -> None:
    past = NOW - timedelta(days=2)
    assert classify_deadline(past, now=NOW) is DeadlinePhase.OVERDUE
    assert deadline_why_now_glance(DeadlinePhase.OVERDUE) == "Overdue"
    today = NOW.replace(hour=18)
    assert classify_deadline(today, now=NOW) is DeadlinePhase.DUE_TODAY


def test_high_priority_reminders_still_collect() -> None:
    brunch = build_reminder(
        id="rem-brunch",
        title="Book Saturday brunch for Elena's parents",
        due_at=NOW + timedelta(days=2),
        priority=5,
    )
    tokens = build_reminder(
        id="rem-tokens",
        title="Draft colour + spacing token inventory",
        due_at=NOW + timedelta(days=1),
        priority=5,
    )
    items = collect_attention_items(reminders=[brunch, tokens])
    ranked = HeuristicAttentionEngine().rank(items)
    surfaced, _ = partition_surface(ranked, now=NOW)
    assert {i.title for i in surfaced} == {
        "Book Saturday brunch for Elena's parents",
        "Draft colour + spacing token inventory",
    }
