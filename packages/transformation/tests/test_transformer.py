"""Tests for Enigma transformation privacy and pseudonym behaviour."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from personal_enigma.domain import (
    PrivateCalendarEvent,
    PrivateNote,
    PrivatePerson,
    PrivatePersonRef,
)
from personal_enigma.fixtures import sample_calendar_event
from personal_enigma.identity import EntityResolver
from personal_enigma.transformation import (
    DefaultEnigmaTransformer,
    StubHmacResolver,
    TransformedContext,
    extract_minimal_passage,
)

FIXED_HMAC_KEY = b"golden-test-hmac-key"


def _serialised(ctx: TransformedContext) -> str:
    return json.dumps(ctx.model_dump(mode="json"), default=str)


def test_transformed_context_defaults_no_remote() -> None:
    ctx = TransformedContext(summary="placeholder")
    assert ctx.may_transmit_remotely is False
    assert ctx.entities == []


def test_stub_resolver_satisfies_entity_resolver_protocol() -> None:
    resolver = StubHmacResolver(FIXED_HMAC_KEY)
    assert isinstance(resolver, EntityResolver)


def test_pseudonym_stable_for_fixed_hmac_key() -> None:
    resolver = StubHmacResolver(FIXED_HMAC_KEY)
    person = PrivatePerson(
        id=uuid4(),
        display_name="Alex Example",
        email_addresses=["alex@example.com"],
        phone_numbers=["+1-555-010-9999"],
    )
    first = resolver.resolve_person(person)
    second = StubHmacResolver(FIXED_HMAC_KEY).resolve_person(person)
    assert str(first) == str(second)
    assert str(first).startswith("PERSON_")
    assert len(str(first)) == len("PERSON_") + 6

    ref_a = resolver.resolve_ref(PrivatePersonRef(email="alex@example.com"))
    ref_b = StubHmacResolver(FIXED_HMAC_KEY).resolve_ref(
        PrivatePersonRef(email="alex@example.com")
    )
    assert ref_a is not None and ref_b is not None
    assert str(ref_a) == str(ref_b)


def test_calendar_transform_redacts_emails_and_phones() -> None:
    transformer = DefaultEnigmaTransformer(hmac_key=FIXED_HMAC_KEY)
    event = PrivateCalendarEvent(
        id="evt_sensitive_1",
        provider="apple_calendar",
        provider_event_id="EK-SENS",
        title="Sync with jordan@corp.example — call +1-555-019-8877",
        description="Confirm with morgan@corp.example",
        start_at=datetime(2026, 8, 16, 14, 0, tzinfo=UTC),
        end_at=datetime(2026, 8, 16, 15, 0, tzinfo=UTC),
        organiser=PrivatePersonRef(
            display_name="Jordan",
            email="jordan@corp.example",
        ),
        attendees=[
            PrivatePersonRef(display_name="Morgan", email="morgan@corp.example"),
        ],
    )
    ctx = transformer.transform(event)
    blob = _serialised(ctx)

    assert "jordan@corp.example" not in blob
    assert "morgan@corp.example" not in blob
    assert "+1-555-019-8877" not in blob
    assert "555-019-8877" not in blob
    assert all(e.startswith("PERSON_") for e in ctx.entities)
    assert ctx.may_transmit_remotely is False
    assert "Calendar:" in ctx.summary


def test_calendar_accepts_dict_and_fixture_model() -> None:
    transformer = DefaultEnigmaTransformer(hmac_key=FIXED_HMAC_KEY)
    fixture = sample_calendar_event()
    from_model = transformer.transform(fixture)
    from_dict = transformer.transform(fixture.model_dump(mode="json"))
    assert from_model.summary == from_dict.summary
    assert from_model.may_transmit_remotely is False
    assert from_model.metadata["source_type"] == "calendar_event"


def test_contact_never_exposes_raw_pii() -> None:
    transformer = DefaultEnigmaTransformer(hmac_key=FIXED_HMAC_KEY)
    person = PrivatePerson(
        id=uuid4(),
        display_name="Sam Sensitive",
        email_addresses=["sam.sensitive@example.com"],
        phone_numbers=["555-010-2222"],
    )
    ctx = transformer.transform(person)
    blob = _serialised(ctx)

    assert "sam.sensitive@example.com" not in blob
    assert "555-010-2222" not in blob
    assert "Sam Sensitive" not in blob
    assert ctx.entities == [ctx.summary.removeprefix("Contact: ")]
    assert ctx.may_transmit_remotely is False


def test_notes_extract_passage_not_wholesale_and_not_remote() -> None:
    long_body = (
        "First paragraph with the only actionable bit.\n\n"
        + ("Secret diary line that must not ship wholesale. " * 40)
    )
    note = PrivateNote(
        id="note_1",
        provider="apple_notes",
        provider_note_id="N-1",
        title="Private journal",
        body_text=long_body,
    )
    transformer = DefaultEnigmaTransformer(hmac_key=FIXED_HMAC_KEY, allow_remote=True)
    ctx = transformer.transform(note)

    assert ctx.may_transmit_remotely is False
    assert ctx.metadata["wholesale_body_included"] is False
    assert long_body not in ctx.summary
    assert "Secret diary line that must not ship wholesale." not in ctx.summary
    assert "First paragraph with the only actionable bit." in ctx.summary
    assert len(ctx.summary) < len(long_body)


def test_extract_minimal_passage_truncates() -> None:
    body = "word " * 200
    passage = extract_minimal_passage(body, max_chars=40)
    assert len(passage) <= 41  # ellipsis
    assert passage.endswith("…")
    assert body.strip() not in passage


def test_allow_remote_still_blocks_high_privacy_sources() -> None:
    transformer = DefaultEnigmaTransformer(hmac_key=FIXED_HMAC_KEY, allow_remote=True)
    person = PrivatePerson(id=uuid4(), display_name="Pat")
    note = PrivateNote(
        id="n2",
        provider="apple_notes",
        provider_note_id="N-2",
        title="Short",
        body_text="tiny",
    )
    assert transformer.transform(person).may_transmit_remotely is False
    assert transformer.transform(note).may_transmit_remotely is False

    event = sample_calendar_event()
    assert transformer.transform(event).may_transmit_remotely is True
