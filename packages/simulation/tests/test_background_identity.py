"""F-background-identity — rewritten cast namespaces + contacts materialisation."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from personal_enigma.domain import PrivatePerson, PrivatePersonRef
from personal_enigma.identity import HmacEntityResolver
from personal_enigma.simulation.corpus.background import (
    build_background_stream,
    canonical_contact_display_names,
    canonical_contact_emails,
    materialise_background_cast,
)
from personal_enigma.simulation.corpus.sanitise import IdentityMapping
from personal_enigma.simulation.scenario import load_scenario
from personal_enigma.simulation.sources.contacts import SyntheticContactsSource

REPO = Path(__file__).resolve().parents[3]
FEATURE = REPO / "scenarios" / "feature" / "background-identity"
FIXED_KEY = b"f-background-identity-hmac-key"

_LABEL_KEYS = frozenset(
    {
        "signal_class",
        "source_class",
        "expected_attention",
        "scenario_source",
        "is_important",
        "importance",
    }
)


def test_background_person_namespace_disjoint_from_canonical_maya() -> None:
    pkg = load_scenario(FEATURE)
    built = build_background_stream(pkg, profile="feature")
    assert built.identities
    assert built.events

    roster_emails = canonical_contact_emails(pkg)
    assert "maya.chen@northwind.example" in roster_emails
    roster_names = canonical_contact_display_names(pkg)
    assert "maya chen" in roster_names

    for mapping in built.identities.values():
        if mapping.person_id == "demo-protagonist":
            continue
        assert mapping.person_id.startswith("background-person-"), mapping.person_id
        assert mapping.person_id != "maya"
        assert mapping.email.endswith(".example")
        assert "@company-" in mapping.email
        assert mapping.email.lower() not in roster_emails
        # Sanitiser rewrites into the demo cast pool (not FinePersonas natives).
        assert mapping.display_name  # non-empty rewritten cast name

    for event in built.events:
        sender = str(event.payload.get("from") or "").lower()
        if sender and sender != "alex.morgan@northwind.example":
            assert sender not in roster_emails
            assert sender != "maya.chen@northwind.example"


def test_display_name_collision_does_not_collapse_maya_namespaces() -> None:
    """Canonical Maya ≠ background Maya even when display_name collides."""
    pkg = load_scenario(FEATURE)
    colliding = IdentityMapping(
        person_id="background-person-4242",
        display_name="Maya Chen",
        email="person-4242@company-007.example",
        source_email="maya.native@finepersonas.invalid",
        source_name="Maya Chen",
    )
    cast = materialise_background_cast(
        {"maya.native@finepersonas.invalid": colliding},
        at=datetime(2026, 4, 7, 8, 2, tzinfo=UTC),
        exclude_emails=canonical_contact_emails(pkg),
    )
    assert len(cast) == 1
    payload = cast[0].payload
    assert payload["id"] == "background-person-4242"
    assert payload["id"] != "maya"
    assert payload["email"] == "person-4242@company-007.example"
    assert payload["email"] != "maya.chen@northwind.example"
    assert payload["display_name"] == "Maya Chen"

    resolver = HmacEntityResolver(FIXED_KEY)
    canonical = PrivatePerson(
        id=uuid4(),
        display_name="Maya Chen",
        email_addresses=["maya.chen@northwind.example"],
        provider_ids={"synthetic": "canonical-maya"},
    )
    background = PrivatePerson(
        id=uuid4(),
        display_name="Maya Chen",
        email_addresses=["person-4242@company-007.example"],
        provider_ids={"synthetic": "background-maya"},
    )
    # Email-only refs stay in disjoint namespaces (PERSON_* differs).
    by_email_canonical = resolver.resolve_ref(
        PrivatePersonRef(email="maya.chen@northwind.example")
    )
    by_email_background = resolver.resolve_ref(
        PrivatePersonRef(email="person-4242@company-007.example")
    )
    assert by_email_canonical is not None
    assert by_email_background is not None
    assert str(by_email_canonical) != str(by_email_background)

    # Full contact records also carry distinct provider anchors + emails.
    # Indexing both with the shared display name would unify — provider+email
    # anchors alone prove the simulation namespaces remain separate.
    resolver_isolated = HmacEntityResolver(FIXED_KEY)
    can_pseudo = resolver_isolated.resolve_person(
        canonical.model_copy(update={"display_name": None})
    )
    bg_pseudo = resolver_isolated.resolve_person(
        background.model_copy(update={"display_name": None})
    )
    assert str(can_pseudo) != str(bg_pseudo)


def test_rewritten_identity_stable_across_messages() -> None:
    pkg = load_scenario(FEATURE)
    built = build_background_stream(pkg, profile="feature")
    by_source: dict[str, IdentityMapping] = {}
    for mapping in built.identities.values():
        key = mapping.source_email.strip().lower()
        if key in by_source:
            prior = by_source[key]
            assert prior.person_id == mapping.person_id
            assert prior.email == mapping.email
            assert prior.display_name == mapping.display_name
        else:
            by_source[key] = mapping

    # Same rewrite seed → same cast on rebuild.
    again = build_background_stream(pkg, profile="feature")
    assert {k: (v.person_id, v.email, v.display_name) for k, v in built.identities.items()} == {
        k: (v.person_id, v.email, v.display_name) for k, v in again.identities.items()
    }


def test_contacts_stream_materialises_cast_without_importance_labels() -> None:
    pkg = load_scenario(FEATURE)
    built = build_background_stream(pkg, profile="feature")
    cast_events = materialise_background_cast(
        built.identities,
        at=datetime(2026, 4, 7, 8, 2, tzinfo=UTC),
        exclude_emails=canonical_contact_emails(pkg),
    )
    assert cast_events
    for event in cast_events:
        assert event.source == "contacts"
        assert event.type == "contact.upsert"
        assert _LABEL_KEYS.isdisjoint(event.payload.keys())
        assert str(event.payload["id"]).startswith("background-person-")

    source = SyntheticContactsSource([*pkg.events, *cast_events])

    async def _run() -> list[dict]:
        batch = await source.get_changes(None)
        return list(batch.items)

    items = asyncio.run(_run())
    bg_items = [
        item
        for item in items
        if any(
            str(e).endswith(".example") and "@company-" in str(e)
            for e in item.get("email_addresses") or []
        )
    ]
    assert bg_items
    for item in items:
        assert _LABEL_KEYS.isdisjoint(item.keys())
        assert "signal_class" not in item
        assert "is_important" not in item
        assert "expected_attention" not in item
