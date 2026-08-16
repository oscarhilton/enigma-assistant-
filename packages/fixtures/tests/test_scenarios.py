"""Scenario pack equality and in-memory store smoke tests."""

from personal_enigma.domain import (
    CalendarEvidence,
    EmailEvidence,
    Obligation,
    ReminderEvidence,
)
from personal_enigma.fixtures import (
    InMemoryFixtureStore,
    get_scenario,
    review_proposal_scenario,
)


def test_review_proposal_scenario_deterministic() -> None:
    a = review_proposal_scenario()
    b = review_proposal_scenario()
    assert a == b
    assert a.name == "review_proposal"
    assert len(a.reminders) == 1
    assert len(a.messages) == 1
    assert len(a.calendar_events) == 1
    assert a.reminders[0].title == "Review proposal"
    assert a.messages[0].id == "msg_review_proposal"
    assert a.calendar_events[0].title == "Proposal review"


def test_review_proposal_expected_obligation() -> None:
    pack = review_proposal_scenario()
    assert pack.expected_obligation is not None
    obligation = pack.expected_obligation
    assert isinstance(obligation, Obligation)
    assert obligation.description == "Review proposal"
    assert obligation.confidence == 0.98
    assert obligation.due_at == pack.reminders[0].due_at
    kinds = [e.kind for e in obligation.evidence]
    assert kinds == ["reminder", "email", "calendar"]
    assert isinstance(obligation.evidence[0], ReminderEvidence)
    assert isinstance(obligation.evidence[1], EmailEvidence)
    assert isinstance(obligation.evidence[2], CalendarEvidence)
    assert obligation.evidence[0].reminder_id == pack.reminders[0].id
    assert obligation.evidence[1].message_id == pack.messages[0].id
    assert obligation.evidence[2].event_id == pack.calendar_events[0].id


def test_get_scenario_registry() -> None:
    pack = get_scenario("review_proposal")
    assert pack.name == "review_proposal"
    assert pack == review_proposal_scenario()


def test_get_scenario_returns_fresh_copies() -> None:
    a = get_scenario("review_proposal")
    b = get_scenario("review_proposal")
    a.metadata["mutated"] = "yes"
    assert "mutated" not in b.metadata


def test_in_memory_store_loads_review_proposal() -> None:
    store = InMemoryFixtureStore()
    pack = store.load_scenario_by_name("review_proposal")
    assert len(store.reminders) == 1
    assert len(store.messages) == 1
    assert len(store.calendar_events) == 1
    assert len(store.contacts) == 1
    assert len(store.notes) == 1
    assert store.reminders[0].id == pack.reminders[0].id
    store.clear()
    assert store.reminders == []
    assert store.messages == []


def test_scenario_pack_equality_snapshot() -> None:
    """Stable structural snapshot for the Review proposal pack."""
    pack = review_proposal_scenario()
    snapshot = {
        "name": pack.name,
        "reminder_ids": [r.id for r in pack.reminders],
        "message_ids": [m.id for m in pack.messages],
        "event_ids": [e.id for e in pack.calendar_events],
        "obligation": pack.expected_obligation.model_dump(mode="json")
        if pack.expected_obligation
        else None,
    }
    assert snapshot == {
        "name": "review_proposal",
        "reminder_ids": ["rem_review_proposal"],
        "message_ids": ["msg_review_proposal"],
        "event_ids": ["evt_review_proposal"],
        "obligation": {
            "description": "Review proposal",
            "due_at": "2026-08-21T17:00:00Z",
            "evidence": [
                {
                    "kind": "reminder",
                    "reminder_id": "rem_review_proposal",
                    "title": "Review proposal",
                },
                {
                    "kind": "email",
                    "message_id": "msg_review_proposal",
                    "subject": "Re: Proposal — can you review before Monday?",
                },
                {
                    "kind": "calendar",
                    "event_id": "evt_review_proposal",
                    "title": "Proposal review",
                },
            ],
            "confidence": 0.98,
        },
    }
