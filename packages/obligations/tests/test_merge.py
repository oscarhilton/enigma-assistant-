"""Cross-source obligation merge — Review proposal + calendar dedupe."""

from __future__ import annotations

from datetime import UTC, datetime

from personal_enigma.attention import AttentionKind
from personal_enigma.domain import (
    CalendarEvidence,
    EmailEvidence,
    ReminderEvidence,
)
from personal_enigma.fixtures import build_calendar_event, review_proposal_scenario
from personal_enigma.obligations import (
    merge_sources,
    merge_sources_to_attention,
    obligation_attention_item,
)


def test_review_proposal_merges_to_one_obligation() -> None:
    pack = review_proposal_scenario()
    assert pack.expected_obligation is not None

    obligations = merge_sources(
        reminders=pack.reminders,
        messages=pack.messages,
        calendar_events=pack.calendar_events,
    )

    assert len(obligations) == 1
    obligation = obligations[0]
    assert obligation.description == "Review proposal"
    assert obligation.due_at == pack.expected_obligation.due_at
    assert obligation.confidence == pack.expected_obligation.confidence
    assert obligation.confidence > 0.0

    kinds = [e.kind for e in obligation.evidence]
    assert kinds == ["reminder", "email", "calendar"]
    assert isinstance(obligation.evidence[0], ReminderEvidence)
    assert isinstance(obligation.evidence[1], EmailEvidence)
    assert isinstance(obligation.evidence[2], CalendarEvidence)
    assert obligation.evidence[0].reminder_id == pack.reminders[0].id
    assert obligation.evidence[1].message_id == pack.messages[0].id
    assert obligation.evidence[2].event_id == pack.calendar_events[0].id
    assert obligation.model_dump(mode="json") == pack.expected_obligation.model_dump(
        mode="json"
    )


def test_review_proposal_single_attention_item_with_narrative() -> None:
    pack = review_proposal_scenario()
    items = merge_sources_to_attention(
        reminders=pack.reminders,
        messages=pack.messages,
        calendar_events=pack.calendar_events,
    )

    assert len(items) == 1
    item = items[0]
    # Reminder evidence is the strongest signal for the merged item.
    assert item.kind == AttentionKind.EXPLICIT_REMINDER
    assert item.title == "Review proposal"
    assert item.score == 0.98
    assert set(item.evidence_ids) == {
        pack.reminders[0].id,
        pack.messages[0].id,
        pack.calendar_events[0].id,
    }
    assert "Reminder: Review proposal" in item.body
    assert "Email: Re: Proposal — can you review before Monday?" in item.body
    assert "Calendar: Proposal review" in item.body
    assert "Due " in item.body


def test_apple_google_calendar_duplicates_one_attention_item() -> None:
    """M12 dedupe + merge: duplicate providers must not double-alert."""
    pack = review_proposal_scenario()
    apple = pack.calendar_events[0]
    google = build_calendar_event(
        id="evt_review_proposal_google",
        provider="google_calendar",
        provider_event_id="gcal-review-proposal",
        calendar_id="gcal_work",
        calendar_name="Work",
        title=apple.title,
        description=apple.description,
        start_at=apple.start_at,
        end_at=apple.end_at,
        organiser=apple.organiser,
        attendees=list(apple.attendees),
        availability=apple.availability,
    )

    obligations = merge_sources(
        reminders=pack.reminders,
        messages=pack.messages,
        calendar_events=[apple, google],
    )
    items = [obligation_attention_item(o) for o in obligations]

    assert len(obligations) == 1
    assert len(items) == 1
    calendar_evidence = [e for e in obligations[0].evidence if e.kind == "calendar"]
    assert len(calendar_evidence) == 1
    assert items[0].title == "Review proposal"


def test_unrelated_sources_remain_separate() -> None:
    pack = review_proposal_scenario()
    other = build_calendar_event(
        id="evt_dentist",
        provider_event_id="EK-dentist",
        title="Dentist appointment",
        start_at=datetime(2026, 8, 25, 10, 0, tzinfo=UTC),
        end_at=datetime(2026, 8, 25, 11, 0, tzinfo=UTC),
    )

    obligations = merge_sources(
        reminders=pack.reminders,
        messages=pack.messages,
        calendar_events=[*pack.calendar_events, other],
    )

    assert len(obligations) == 2
    descriptions = {o.description for o in obligations}
    assert "Review proposal" in descriptions
    assert "Dentist appointment" in descriptions
