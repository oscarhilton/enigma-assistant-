from datetime import UTC, datetime, timedelta

from personal_enigma.attention import AttentionKind
from personal_enigma.domain import PrivateMessage, PrivateNote, PrivateReminder
from personal_enigma.obligations.commitments import (
    CommitmentKind,
    CommitmentState,
    CommitmentTracker,
)


def test_explicit_reminder_vs_inferred() -> None:
    now = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
    tracker = CommitmentTracker()
    rem = tracker.upsert_from_reminder(
        PrivateReminder(
            id="r1",
            provider="apple_reminders",
            provider_id="EK-r1",
            title="Send notes",
            due_at=now + timedelta(days=1),
        ),
        now=now,
    )
    msg = tracker.upsert_inferred_from_message(
        PrivateMessage(
            id="m1",
            provider="gmail",
            provider_message_id="g1",
            subject="I'll send that tomorrow",
        ),
        now=now,
    )
    assert rem.kind == CommitmentKind.EXPLICIT_REMINDER
    assert msg.kind == CommitmentKind.INFERRED


def test_completed_reminder_closes_commitment() -> None:
    now = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
    tracker = CommitmentTracker()
    tracker.upsert_from_reminder(
        PrivateReminder(
            id="r1",
            provider="apple_reminders",
            provider_id="EK-r1",
            title="Send notes",
            is_completed=True,
            completed_at=now,
        ),
        now=now,
    )
    assert tracker.open_and_stale() == []


def test_stale_after_due_date_apple_only() -> None:
    now = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
    tracker = CommitmentTracker()
    tracker.upsert_from_reminder(
        PrivateReminder(
            id="r1",
            provider="apple_reminders",
            provider_id="EK-r1",
            title="Call dentist",
            due_at=now - timedelta(hours=1),
        ),
        now=now - timedelta(days=1),
    )
    stale = tracker.refresh_staleness(now=now)
    assert len(stale) == 1
    assert stale[0].state == CommitmentState.STALE
    items = tracker.stale_attention_items()
    assert items[0].kind == AttentionKind.EXPLICIT_REMINDER
    assert items[0].title.startswith("Stale:")


def test_notes_deferred_until_prerequisite() -> None:
    now = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
    tracker = CommitmentTracker()
    note = PrivateNote(
        id="n1",
        provider="apple_notes",
        provider_note_id="N1",
        title="Deferred",
        body_text="Talk to PERSON about PROJECT once migration completes.",
    )
    commitment = tracker.register_deferred_note(
        note,
        description="Talk about PROJECT after migration",
        now=now,
    )
    assert commitment.prerequisite_met is False
    # Not stale while prerequisite unmet, even if we invent a due date later.
    assert tracker.refresh_staleness(now=now + timedelta(days=10)) == []
    tracker.mark_prerequisite_met("n1", now=now)
    open_items = tracker.open_and_stale()
    assert len(open_items) == 1
    assert open_items[0].prerequisite_met is True


def test_follow_up_email_appends_evidence() -> None:
    now = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
    tracker = CommitmentTracker()
    tracker.upsert_from_reminder(
        PrivateReminder(
            id="r1",
            provider="apple_reminders",
            provider_id="EK-r1",
            title="Review proposal",
            due_at=now + timedelta(days=2),
        ),
        now=now,
    )
    updated = tracker.apply_follow_up_email(
        PrivateMessage(
            id="m2",
            provider="gmail",
            provider_message_id="g2",
            subject="Just checking on the proposal",
        ),
        "rem:r1",
        now=now,
    )
    assert updated is not None
    assert "m2" in updated.evidence_ids
