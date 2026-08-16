"""Obligation merge surface rules — F-* merge / pollution regressions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from personal_enigma.attention import AttentionKind, partition_surface
from personal_enigma.fixtures import build_calendar_event, build_message, build_reminder
from personal_enigma.obligations import merge_sources, merge_sources_to_attention

NOW = datetime(2026, 1, 20, 12, 0, tzinfo=UTC)


def test_f_calendar_existence_not_merged_to_obligation() -> None:
    events = [
        build_calendar_event(
            id="cal-standup",
            title="Team standup",
            start_at=NOW + timedelta(hours=1),
            end_at=NOW + timedelta(hours=1, minutes=15),
        ),
        build_calendar_event(
            id="cal-maya",
            provider_event_id="EK-1-1",
            title="1:1 Maya",
            start_at=NOW + timedelta(days=1),
            end_at=NOW + timedelta(days=1, hours=1),
        ),
    ]
    assert merge_sources(calendar_events=events, now=NOW) == []
    assert merge_sources_to_attention(calendar_events=events, now=NOW) == []


def test_f_past_calendar_event_resolves_in_merge() -> None:
    past = build_calendar_event(
        id="cal-jan5",
        title="Team standup",
        start_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
        end_at=datetime(2026, 1, 5, 9, 15, tzinfo=UTC),
    )
    assert merge_sources(calendar_events=[past], now=NOW) == []


def test_f_unrelated_machine_mail_not_merged() -> None:
    """F-unrelated-machine-mail-not-merged: PrizeVault cluster must not coalesce."""
    messages = [
        build_message(
            id="msg-prize-1",
            subject="PrizeVault: you won",
            snippet="Claim now",
            body_text="PrizeVault offer A",
            from_person={"display_name": "PrizeVault", "email": "wins@prizevault.example"},
        ),
        build_message(
            id="msg-prize-2",
            subject="PrizeVault: last chance",
            snippet="Claim now",
            body_text="PrizeVault offer B",
            from_person={"display_name": "PrizeVault", "email": "wins@prizevault.example"},
        ),
        build_message(
            id="msg-build",
            subject="BuildCloud: build #9 passed",
            snippet="Build #9 passed",
            body_text="BuildCloud CI notification",
            from_person={"display_name": "BuildCloud", "email": "noreply@buildcloud.example"},
        ),
    ]
    assert merge_sources(messages=messages) == []
    assert merge_sources_to_attention(messages=messages) == []


def test_f_distinct_social_plans_not_merged() -> None:
    """F-distinct-social-plans-not-merged: Dinner Thursday? ≠ Climbing Sunday?."""
    dinner = build_message(
        id="msg-dinner",
        subject="Dinner Thursday?",
        snippet="Dinner Thursday?",
        body_text="Want to grab dinner Thursday?",
        from_person={"display_name": "Elena Vargas", "email": "elena@example.test"},
    )
    climbing = build_message(
        id="msg-climb",
        subject="Climbing Sunday?",
        snippet="Climbing Sunday?",
        body_text="Climbing Sunday morning?",
        from_person={"display_name": "Tom Reed", "email": "tom@example.test"},
    )
    items = merge_sources_to_attention(messages=[dinner, climbing])
    assert len(items) == 2
    titles = {i.title for i in items}
    assert "Dinner Thursday?" in titles
    assert "Climbing Sunday?" in titles
    assert all(i.kind == AttentionKind.PENDING_REPLY for i in items)


def test_brunch_and_tokens_surface_calendar_context_without_bare_events() -> None:
    """Target moment: ~2 HIGH reminders; bare calendar does not inflate count."""
    brunch = build_reminder(
        id="rem-brunch",
        title="Book Saturday brunch for Elena's parents",
        due_at=datetime(2026, 1, 22, 12, 0, tzinfo=UTC),
        priority=5,
    )
    tokens = build_reminder(
        id="rem-tokens",
        title="Draft colour + spacing token inventory",
        due_at=datetime(2026, 1, 21, 17, 0, tzinfo=UTC),
        priority=5,
    )
    sync = build_message(
        id="msg-sync",
        subject="Quick sync next week?",
        snippet="Quick sync next week?",
        body_text="Quick sync next week?",
        from_person={"display_name": "Maya Chen", "email": "maya@northwind.example"},
    )
    events = [
        build_calendar_event(
            id="cal-standup",
            title="Team standup",
            start_at=NOW + timedelta(hours=2),
            end_at=NOW + timedelta(hours=2, minutes=15),
        ),
        build_calendar_event(
            id="cal-brunch",
            provider_event_id="EK-brunch",
            title="Brunch with Elena's parents",
            start_at=datetime(2026, 1, 24, 11, 0, tzinfo=UTC),
            end_at=datetime(2026, 1, 24, 13, 0, tzinfo=UTC),
        ),
        build_calendar_event(
            id="cal-dinner",
            provider_event_id="EK-dinner",
            title="Dinner with Elena",
            start_at=datetime(2026, 1, 22, 19, 0, tzinfo=UTC),
            end_at=datetime(2026, 1, 22, 21, 0, tzinfo=UTC),
        ),
        build_calendar_event(
            id="cal-climb",
            provider_event_id="EK-climb",
            title="Climbing with Tom",
            start_at=datetime(2026, 1, 25, 10, 0, tzinfo=UTC),
            end_at=datetime(2026, 1, 25, 12, 0, tzinfo=UTC),
        ),
    ]
    items = merge_sources_to_attention(
        reminders=[brunch, tokens],
        messages=[sync],
        calendar_events=events,
        now=NOW,
    )
    surfaced, held = partition_surface(items, now=NOW)
    surfaced_titles = {i.title for i in surfaced}
    assert surfaced_titles == {
        "Book Saturday brunch for Elena's parents",
        "Draft colour + spacing token inventory",
    }
    assert len(surfaced) == 2
    assert all("standup" not in i.title.casefold() for i in items)
    assert all("Climbing with Tom" not in i.title for i in surfaced)
    assert any(i.kind == AttentionKind.PENDING_REPLY for i in (*held, *items))
