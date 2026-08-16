"""F-correctness wave: threading, identity, canonical isolation (mini fixtures)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

from personal_enigma.evaluation import ScenarioSignalClass, load_ground_truth
from personal_enigma.simulation.corpus.background import (
    build_background_stream,
    canonical_contact_emails,
    materialise_background_cast,
)
from personal_enigma.simulation.corpus.models import CorpusConversation, CorpusMessage
from personal_enigma.simulation.corpus.sanitise import sanitise_conversation_detailed
from personal_enigma.simulation.corpus.timeline import place_conversation_on_timeline
from personal_enigma.simulation.scenario import load_scenario
from personal_enigma.simulation.sources.contacts import SyntheticContactsSource
from personal_enigma.simulation.sources.mail import SyntheticMailSource

REPO = Path(__file__).resolve().parents[3]
FEATURE = REPO / "scenarios" / "feature"

EVALUATOR_KEYS = frozenset(
    {
        "signal_class",
        "source_class",
        "expected_attention",
        "scenario_source",
        "is_important",
    }
)


def test_background_threading_stable_ids_and_order() -> None:
    pkg = load_scenario(FEATURE / "background-threading")
    assert pkg.manifest.id == "background-threading"
    built = build_background_stream(pkg, profile="feature")
    assert built.events

    by_thread: dict[str, list] = {}
    for event in built.events:
        thread = str(event.payload["thread_id"])
        by_thread.setdefault(thread, []).append(event)
        # Payload id shares the conversation id prefix used as thread_id.
        assert str(event.payload["id"]).startswith(f"{thread}-")

    multi = {tid: evs for tid, evs in by_thread.items() if len(evs) > 1}
    assert multi, "expected at least one multi-message mini thread"

    for thread_id, events in multi.items():
        assert all(e.payload["thread_id"] == thread_id for e in events)
        stamps = [e.at for e in events]
        assert stamps == sorted(stamps)
        assert all(stamps[i] < stamps[i + 1] for i in range(len(stamps) - 1))


def test_background_threading_window_edge_preserves_reply_order() -> None:
    """Tight window still yields strictly increasing reply stamps."""
    conv = CorpusConversation(
        id="edge-thread",
        messages=[
            CorpusMessage(
                corpus_id="finepersonas-mini",
                conversation_id="edge-thread",
                message_index=i,
                sender_name="Casey Ng",
                sender_email="casey@riverside-college.edu",
                recipient_names=["Alex Morgan"],
                recipient_emails=["alex.morgan@northwind.example"],
                subject=f"Re: edge {i}",
                body_text=f"reply {i}",
            )
            for i in range(5)
        ],
    )
    cleaned = sanitise_conversation_detailed(
        conv,
        rewrite_seed="f-threading-edge",
        self_email="alex.morgan@northwind.example",
    ).conversation
    assert cleaned is not None
    start = datetime(2026, 4, 6, 16, 0, tzinfo=UTC)
    end = start + timedelta(minutes=2)
    placed = place_conversation_on_timeline(
        cleaned,
        window_start=start,
        window_end=end,
        seed="f-threading-edge",
        self_email="alex.morgan@northwind.example",
    )
    assert len(placed) == 5
    assert all(e.payload["thread_id"] == "edge-thread" for e in placed)
    stamps = [e.at for e in placed]
    assert stamps == sorted(stamps)
    assert all(stamps[i] < stamps[i + 1] for i in range(len(stamps) - 1))


def test_background_identity_rewritten_cast_consistent_and_disjoint() -> None:
    pkg = load_scenario(FEATURE / "background-identity")
    built = build_background_stream(pkg, profile="feature")
    assert built.identities
    roster = canonical_contact_emails(pkg)
    self_email = "alex.morgan@northwind.example"

    # Same source email maps to one rewritten identity.
    by_person: dict[str, set[str]] = {}
    for mapping in built.identities.values():
        by_person.setdefault(mapping.person_id, set()).add(mapping.email)
    assert all(len(emails) == 1 for emails in by_person.values())

    for event in built.events:
        sender = str(event.payload.get("from") or "").lower()
        if sender and sender != self_email.lower():
            assert sender not in roster
            assert sender.endswith(".example")
            assert "acme-widgets.com" not in sender
            assert "northstar-design.io" not in sender
            assert "riverside-college.edu" not in sender
        from_name = str(event.payload.get("from_name") or "")
        assert "Jordan Lee" not in from_name
        assert "Sam Rivera" not in from_name
        assert "Casey Ng" not in from_name


def test_background_identity_cast_materialises_via_contacts() -> None:
    pkg = load_scenario(FEATURE / "background-identity")
    built = build_background_stream(pkg, profile="feature")
    cast_events = materialise_background_cast(
        built.identities,
        at=datetime(2026, 4, 7, 8, 30, tzinfo=UTC),
        exclude_emails=canonical_contact_emails(pkg),
    )
    assert cast_events
    for event in cast_events:
        assert event.source == "contacts"
        assert event.type == "contact.upsert"
        assert EVALUATOR_KEYS.isdisjoint(event.payload.keys())
        assert str(event.payload["email"]).endswith(".example")
        assert str(event.payload["id"]).startswith("background-person-")

    async def _run() -> list[dict]:
        source = SyntheticContactsSource(cast_events)
        batch = await source.get_changes(None)
        return list(batch.items)

    people = asyncio.run(_run())
    assert len(people) == len(cast_events)
    for person in people:
        assert EVALUATOR_KEYS.isdisjoint(person.keys())
        emails = person.get("email_addresses") or []
        assert emails
        assert all(str(e).endswith(".example") for e in emails)


def test_background_canonical_isolation_mail_omits_evaluator_keys() -> None:
    pkg = load_scenario(FEATURE / "background-canonical-isolation")
    gt_root = FEATURE / "background-canonical-isolation" / "ground_truth"
    truth = load_ground_truth(gt_root)
    assert truth.obligations
    canonical = truth.signals_for_class(ScenarioSignalClass.CANONICAL)
    assert any(s.evidence_id == "mail-isolation-critical" for s in canonical)
    assert all(s.expected_attention is True for s in canonical)

    # Ground-truth store is a sibling directory — never mixed into scenario events.
    assert (gt_root).is_dir()
    assert gt_root.parent == pkg.root
    for event in pkg.events:
        assert EVALUATOR_KEYS.isdisjoint(event.payload.keys())

    source = SyntheticMailSource.for_scenario(pkg, profile="feature", include_noise=False)

    async def _run() -> list[dict]:
        batch = await source.get_changes(None)
        return list(batch.items)

    items = asyncio.run(_run())
    assert items
    assert any(
        (item.get("provider_message_id") == "mail-isolation-critical")
        or (item.get("subject") and "Board pack" in str(item.get("subject")))
        for item in items
    )
    for item in items:
        assert EVALUATOR_KEYS.isdisjoint(item.keys())
        # Nested dumps must also stay clean.
        blob = str(item)
        assert "signal_class" not in blob
        assert "expected_attention" not in blob


def test_background_basic_and_no_alert_remain_green() -> None:
    """Correctness wave bookends already on main — keep them in the gate."""
    basic = load_scenario(FEATURE / "background-basic")
    assert basic.manifest.id == "background-basic"
    mail = [e for e in basic.events if e.type == "email.receive"]
    assert sum(1 for e in mail if "Thread chatter" in str(e.payload.get("subject"))) >= 50
    assert any("Lease renewal" in str(e.payload.get("subject")) for e in mail)
    for event in mail:
        assert EVALUATOR_KEYS.isdisjoint(event.payload.keys())

    no_alert = load_scenario(FEATURE / "background-no-alert")
    truth = load_ground_truth(FEATURE / "background-no-alert" / "ground_truth")
    assert no_alert.manifest.id == "background-no-alert"
    assert truth.obligations == []
