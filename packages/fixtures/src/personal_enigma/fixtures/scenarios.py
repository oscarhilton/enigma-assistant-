"""Cross-source scenario packs for deterministic obligation / attention tests.

Scenario packs group related synthetic entities that later milestones (M06,
M15) merge into obligations. All data is synthetic and fixed for equality /
snapshot tests.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from personal_enigma.domain import (
    CalendarEvidence,
    EmailEvidence,
    Obligation,
    PrivateCalendarEvent,
    PrivateMessage,
    PrivateNote,
    PrivatePerson,
    PrivateReminder,
    ReminderEvidence,
)
from personal_enigma.fixtures.builders import (
    build_calendar_event,
    build_contact,
    build_message,
    build_note,
    build_person_ref,
    build_reminder,
)

# Timeline for the canonical "Review proposal" case (UTC):
# - Thu 20 Aug 2026: email follow-up
# - Fri 21 Aug 2026: reminder due (friday before meeting)
# - Mon 24 Aug 2026: proposal review meeting
REVIEW_PROPOSAL_EMAIL_AT = datetime(2026, 8, 20, 15, 30, tzinfo=UTC)
REVIEW_PROPOSAL_DUE_AT = datetime(2026, 8, 21, 17, 0, tzinfo=UTC)
REVIEW_PROPOSAL_MEETING_START = datetime(2026, 8, 24, 14, 0, tzinfo=UTC)
REVIEW_PROPOSAL_MEETING_END = datetime(2026, 8, 24, 15, 0, tzinfo=UTC)

REVIEW_PROPOSAL_REMINDER_ID = "rem_review_proposal"
REVIEW_PROPOSAL_MESSAGE_ID = "msg_review_proposal"
REVIEW_PROPOSAL_EVENT_ID = "evt_review_proposal"


@dataclass(frozen=True)
class ScenarioPack:
    """Named bundle of synthetic entities for one test scenario."""

    name: str
    description: str
    calendar_events: tuple[PrivateCalendarEvent, ...] = ()
    reminders: tuple[PrivateReminder, ...] = ()
    contacts: tuple[PrivatePerson, ...] = ()
    notes: tuple[PrivateNote, ...] = ()
    messages: tuple[PrivateMessage, ...] = ()
    expected_obligation: Obligation | None = None
    metadata: dict[str, str] = field(default_factory=dict)


def review_proposal_scenario() -> ScenarioPack:
    """Cross-source pack: reminder + email + calendar → one obligation.

    Used by M15 ("Review proposal" fixture → one Obligation with typed
    evidence). Due date is the Friday before the Monday meeting.
    """
    organiser = build_person_ref(
        display_name="Alex Chen",
        email="alex.chen@example.test",
        provider_id="person_ref_alex",
    )
    self_ref = build_person_ref(
        display_name="Sam Rivera",
        email="sam.rivera@example.test",
        provider_id="person_ref_sam",
    )

    reminder = build_reminder(
        id=REVIEW_PROPOSAL_REMINDER_ID,
        provider_id="REM-review-proposal",
        title="Review proposal",
        notes="Finish before Monday's review meeting.",
        due_at=REVIEW_PROPOSAL_DUE_AT,
        list_id="list_work",
        priority=1,
    )
    message = build_message(
        id=REVIEW_PROPOSAL_MESSAGE_ID,
        provider_message_id="gmail-review-proposal",
        thread_id="thread_review_proposal",
        subject="Re: Proposal — can you review before Monday?",
        snippet="Can you review the proposal before Monday's meeting?",
        body_text=(
            "Hi Sam,\n\n"
            "Can you review the attached proposal before Monday's meeting?\n\n"
            "Thanks,\nAlex\n"
        ),
        from_person=organiser,
        to=[self_ref],
        sent_at=REVIEW_PROPOSAL_EMAIL_AT,
        received_at=REVIEW_PROPOSAL_EMAIL_AT,
        labels=["INBOX", "IMPORTANT"],
    )
    event = build_calendar_event(
        id=REVIEW_PROPOSAL_EVENT_ID,
        provider_event_id="EK-review-proposal",
        calendar_id="cal_work",
        calendar_name="Work",
        title="Proposal review",
        description="Walk through the draft proposal.",
        start_at=REVIEW_PROPOSAL_MEETING_START,
        end_at=REVIEW_PROPOSAL_MEETING_END,
        organiser=organiser,
        attendees=[self_ref, organiser],
        availability="busy",
    )
    contact = build_contact(
        display_name="Alex Chen",
        aliases=["A. Chen"],
        email_addresses=["alex.chen@example.test"],
        organisations=["Example Corp"],
        provider_ids={"apple_contacts": "AB-alex-chen"},
    )
    note = build_note(
        id="note_review_proposal",
        provider_note_id="NOTE-review-proposal",
        folder="Work",
        title="Proposal talking points",
        body_text="Draft notes for the proposal review meeting.",
    )

    expected = Obligation(
        description="Review proposal",
        due_at=REVIEW_PROPOSAL_DUE_AT,
        evidence=[
            ReminderEvidence(
                reminder_id=REVIEW_PROPOSAL_REMINDER_ID,
                title="Review proposal",
            ),
            EmailEvidence(
                message_id=REVIEW_PROPOSAL_MESSAGE_ID,
                subject="Re: Proposal — can you review before Monday?",
            ),
            CalendarEvidence(
                event_id=REVIEW_PROPOSAL_EVENT_ID,
                title="Proposal review",
            ),
        ],
        confidence=0.98,
    )

    return ScenarioPack(
        name="review_proposal",
        description=(
            "Reminder, email follow-up, and calendar meeting that should merge "
            "into a single Review proposal obligation (M15)."
        ),
        calendar_events=(event,),
        reminders=(reminder,),
        contacts=(contact,),
        notes=(note,),
        messages=(message,),
        expected_obligation=expected,
        metadata={"milestone": "M15"},
    )


SCENARIO_REGISTRY: dict[str, Callable[[], ScenarioPack]] = {
    "review_proposal": review_proposal_scenario,
}


def get_scenario(name: str) -> ScenarioPack:
    """Return a fresh registered scenario pack by name (never a shared instance)."""
    try:
        factory = SCENARIO_REGISTRY[name]
    except KeyError as exc:
        known = ", ".join(sorted(SCENARIO_REGISTRY))
        raise KeyError(f"Unknown scenario {name!r}; known: {known}") from exc
    return factory()
