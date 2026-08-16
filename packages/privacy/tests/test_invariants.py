"""Privacy invariant suite — remote payload gate over transformed corpora."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from pydantic import BaseModel

from personal_enigma.domain import PrivateNote, PrivatePerson, SourceType
from personal_enigma.fixtures import (
    build_calendar_event,
    build_contact,
    build_message,
    build_note,
    build_person_ref,
    build_reminder,
    get_scenario,
)
from personal_enigma.privacy import (
    REMOTE_PAYLOAD_ALLOWLIST_DOC,
    REMOTE_PAYLOAD_TOP_LEVEL_KEYS,
    NotesRemotePolicyException,
    PrivacyInvariantError,
    PrivacyLevel,
    RemoteInferenceConfig,
    assert_no_private_person_fields,
    assert_notes_not_wholesale_remote_safe,
    assert_remote_payload_allowlisted,
    assert_remote_payload_safe,
    assert_transformed_corpus_safe,
    default_level_for_source,
    may_send_remotely,
    wholesale_note_body_remote_safe,
)
from personal_enigma.transformation import DefaultEnigmaTransformer, TransformedContext

FIXED_HMAC_KEY = b"m04-privacy-invariant-hmac-key"


def _blob(ctx: TransformedContext) -> str:
    return json.dumps(ctx.model_dump(mode="json"), default=str)


def _corpus_records() -> list[BaseModel]:
    scenario = get_scenario("review_proposal")
    records: list[BaseModel] = [
        *scenario.calendar_events,
        *scenario.reminders,
        *scenario.contacts,
        *scenario.notes,
        *scenario.messages,
        build_calendar_event(
            id="evt_pii",
            title="Sync with jordan@corp.example — call +1-555-019-8877",
            description="Confirm with morgan@corp.example",
            organiser=build_person_ref(
                display_name="Jordan",
                email="jordan@corp.example",
                provider_id="person_ref_jordan",
            ),
            attendees=[
                build_person_ref(
                    display_name="Morgan",
                    email="morgan@corp.example",
                    provider_id="person_ref_morgan",
                )
            ],
        ),
        build_reminder(id="rem_extra", title="Ship privacy gate"),
        build_note(
            id="note_long",
            title="Private journal",
            body_text=(
                "First actionable paragraph.\n\n"
                + ("Secret diary line that must not ship wholesale. " * 40)
            ),
        ),
        build_contact(
            id=uuid4(),
            display_name="Sam Sensitive",
            aliases=["Sammy"],
            email_addresses=["sam.sensitive@example.com"],
            phone_numbers=["555-010-2222"],
            organisations=["Sensitive Org"],
            provider_ids={"apple_contacts": "AB-sam-sensitive"},
        ),
        build_message(
            id="msg_extra",
            subject="Hello",
            snippet="Ping jordan@corp.example",
            body_text="Please call +1-555-019-8877",
            from_person=build_person_ref(email="jordan@corp.example"),
        ),
    ]
    return records


def _people_from_corpus(records: list[BaseModel]) -> list[PrivatePerson]:
    people = [r for r in records if isinstance(r, PrivatePerson)]
    people.append(
        build_contact(
            display_name="Jordan",
            email_addresses=["jordan@corp.example"],
            phone_numbers=["+1-555-019-8877"],
        )
    )
    people.append(
        build_contact(
            display_name="Morgan",
            email_addresses=["morgan@corp.example"],
        )
    )
    return people


def _notes_from_corpus(records: list[BaseModel]) -> list[PrivateNote]:
    return [r for r in records if isinstance(r, PrivateNote)]


def test_allowlist_is_documented() -> None:
    assert "Allowed top-level keys" in REMOTE_PAYLOAD_ALLOWLIST_DOC
    assert "Forbidden in remote payloads" in REMOTE_PAYLOAD_ALLOWLIST_DOC
    assert "summary" in REMOTE_PAYLOAD_TOP_LEVEL_KEYS
    assert "entities" in REMOTE_PAYLOAD_TOP_LEVEL_KEYS


def test_notes_and_contacts_default_high() -> None:
    assert default_level_for_source(SourceType.NOTE) == PrivacyLevel.HIGH
    assert default_level_for_source(SourceType.CONTACT) == PrivacyLevel.HIGH


def test_transformed_fixture_corpus_has_no_private_person_leakage() -> None:
    transformer = DefaultEnigmaTransformer(hmac_key=FIXED_HMAC_KEY, allow_remote=True)
    records = _corpus_records()
    people = _people_from_corpus(records)
    notes = _notes_from_corpus(records)
    payloads = [transformer.transform(record) for record in records]

    remote_payloads = [p for p in payloads if p.may_transmit_remotely]
    assert remote_payloads, "expected some medium-privacy sources to allow remote when enabled"

    assert_transformed_corpus_safe(
        payloads,
        people=people,
        notes=notes,
        remote=RemoteInferenceConfig(enabled=True),
    )

    for ctx in remote_payloads:
        blob = _blob(ctx)
        assert "jordan@corp.example" not in blob
        assert "morgan@corp.example" not in blob
        assert "sam.sensitive@example.com" not in blob
        assert "+1-555-019-8877" not in blob
        assert "555-010-2222" not in blob


def test_negative_raw_private_person_fields_fail_invariant() -> None:
    person = build_contact(
        display_name="Leak Me",
        email_addresses=["leak.me@example.test"],
        phone_numbers=["+1-555-010-9999"],
    )
    dirty = TransformedContext(
        summary=f"Talk to {person.display_name} at {person.email_addresses[0]}",
        entities=["PERSON_ABCDEF"],
        metadata={"source_type": "calendar_event", "record_id": "evt_x"},
        may_transmit_remotely=True,
    )
    with pytest.raises(PrivacyInvariantError, match="PrivatePerson|email"):
        assert_no_private_person_fields(dirty, [person])
    with pytest.raises(PrivacyInvariantError):
        assert_remote_payload_safe(dirty, people=[person])


def test_negative_non_allowlisted_keys_fail() -> None:
    dirty = {
        "summary": "ok",
        "entities": [],
        "metadata": {},
        "may_transmit_remotely": False,
        "email_addresses": ["nope@example.test"],
    }
    with pytest.raises(PrivacyInvariantError, match="non-allowlisted"):
        assert_remote_payload_allowlisted(dirty)


def test_wholesale_note_body_cannot_be_remote_safe_without_exception() -> None:
    body = "Secret diary line that must not ship wholesale. " * 20
    note = build_note(id="note_secret", title="Journal", body_text=body)
    dirty = TransformedContext(
        summary=f"Note: Journal | {body}",
        entities=[],
        metadata={
            "source_type": SourceType.NOTE.value,
            "record_id": note.id,
            "provider": "apple_notes",
            "wholesale_body_included": True,
            "body_chars": len(body),
            "passage_chars": len(body),
        },
        may_transmit_remotely=True,
    )
    with pytest.raises(
        PrivacyInvariantError,
        match="NotesRemotePolicyException|remote-safe|Wholesale",
    ):
        assert_notes_not_wholesale_remote_safe(dirty, note)

    with pytest.raises(PrivacyInvariantError):
        assert_remote_payload_safe(dirty, notes=[note])

    passage_exc = NotesRemotePolicyException(note_id=note.id, reason="audited passage only")
    with pytest.raises(PrivacyInvariantError, match="Wholesale"):
        assert_notes_not_wholesale_remote_safe(dirty, note, policy_exception=passage_exc)

    assert wholesale_note_body_remote_safe(body_text=body, candidate_text=body) is False
    assert (
        wholesale_note_body_remote_safe(
            body_text=body,
            candidate_text="Secret diary line that must not ship wholesale.",
            exception=passage_exc,
        )
        is True
    )


def test_notes_policy_exception_rejects_wholesale_flag() -> None:
    with pytest.raises(ValueError, match="passage_only"):
        NotesRemotePolicyException(note_id="n", reason="x", passage_only=False)


def test_transformer_notes_never_remote_even_with_allow_remote() -> None:
    transformer = DefaultEnigmaTransformer(hmac_key=FIXED_HMAC_KEY, allow_remote=True)
    note = build_note(
        body_text="First paragraph only.\n\n" + ("pad " * 200),
    )
    ctx = transformer.transform(note)
    assert ctx.may_transmit_remotely is False
    assert ctx.metadata.get("wholesale_body_included") is False
    assert note.body_text not in ctx.summary
    assert_remote_payload_safe(ctx, notes=[note], people=[])


def test_remote_inference_disabled_keeps_apple_paths_testable() -> None:
    """Apple sources still transform; nothing is actually sent remotely."""
    remote = RemoteInferenceConfig(enabled=False)
    transformer = DefaultEnigmaTransformer(hmac_key=FIXED_HMAC_KEY, allow_remote=False)

    apple_records = [
        build_calendar_event(provider="apple_calendar"),
        build_reminder(),
        build_contact(),
        build_note(),
    ]
    payloads = [transformer.transform(record) for record in apple_records]
    assert all(p.may_transmit_remotely is False for p in payloads)

    for ctx in payloads:
        assert may_send_remotely(remote, payload_allows_remote=ctx.may_transmit_remotely) is False
        assert_remote_payload_safe(
            ctx,
            people=[r for r in apple_records if isinstance(r, PrivatePerson)],
            notes=[r for r in apple_records if isinstance(r, PrivateNote)],
            remote=remote,
        )

    claimed = TransformedContext(
        summary="Calendar: Fixture meeting",
        entities=[],
        metadata={"source_type": "calendar_event", "record_id": "evt_1"},
        may_transmit_remotely=True,
    )
    assert may_send_remotely(remote, payload_allows_remote=True) is False
    assert_remote_payload_safe(claimed, remote=remote)


def test_missing_source_type_cannot_claim_remote() -> None:
    claimed = TransformedContext(
        summary="Anonymous payload",
        entities=[],
        metadata={},
        may_transmit_remotely=True,
    )
    with pytest.raises(PrivacyInvariantError, match="source_type"):
        assert_remote_payload_safe(claimed)
