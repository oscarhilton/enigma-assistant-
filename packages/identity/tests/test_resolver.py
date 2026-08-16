from __future__ import annotations

from uuid import uuid4

import pytest

from personal_enigma.domain import PrivatePerson, PrivatePersonRef
from personal_enigma.identity import (
    EntityResolver,
    HmacEntityResolver,
    Pseudonym,
    assert_remote_entities_safe,
    is_person_pseudonym,
)

FIXED_KEY = b"m10-identity-test-hmac-key"


def test_pseudonym_str() -> None:
    assert str(Pseudonym(value="PERSON_A4F91C")) == "PERSON_A4F91C"


def test_hmac_resolver_satisfies_protocol() -> None:
    resolver = HmacEntityResolver(FIXED_KEY)
    assert isinstance(resolver, EntityResolver)


def test_email_invite_name_and_contact_unify_to_one_person() -> None:
    """joe@example.com + \"Joe\" + \"Joseph Atkinson\" → one PERSON id."""
    resolver = HmacEntityResolver(FIXED_KEY)
    contact = PrivatePerson(
        id=uuid4(),
        display_name="Joseph Atkinson",
        aliases=["Joe"],
        email_addresses=["joe@example.com"],
        provider_ids={"apple_contacts": "AB-joseph"},
    )
    from_contact = resolver.resolve_person(contact)

    from_email = resolver.resolve_ref(PrivatePersonRef(email="joe@example.com"))
    from_short = resolver.resolve_ref(PrivatePersonRef(display_name="Joe"))
    from_full = resolver.resolve_ref(PrivatePersonRef(display_name="Joseph Atkinson"))

    assert from_email is not None
    assert from_short is not None
    assert from_full is not None
    assert str(from_contact) == str(from_email) == str(from_short) == str(from_full)
    assert is_person_pseudonym(str(from_contact))
    assert str(from_contact).startswith("PERSON_")
    assert len(str(from_contact)) == len("PERSON_") + 6


def test_unification_stable_across_resolver_instances_with_same_index() -> None:
    person = PrivatePerson(
        id=uuid4(),
        display_name="Joseph Atkinson",
        aliases=["Joe"],
        email_addresses=["joe@example.com"],
    )
    a = HmacEntityResolver(FIXED_KEY)
    b = HmacEntityResolver(FIXED_KEY)
    a.index([person])
    b.index([person])
    assert str(a.resolve_ref(PrivatePersonRef(email="JOE@example.com"))) == str(
        b.resolve_ref(PrivatePersonRef(display_name="joe"))
    )


def test_remote_payload_builder_rejects_raw_private_person() -> None:
    resolver = HmacEntityResolver(FIXED_KEY)
    person = PrivatePerson(
        id=uuid4(),
        display_name="Sam Sensitive",
        email_addresses=["sam@example.com"],
    )
    pseudo = resolver.resolve_person(person)

    with pytest.raises(ValueError, match="PrivatePerson"):
        assert_remote_entities_safe([person])

    with pytest.raises(ValueError, match="PERSON_"):
        assert_remote_entities_safe(["sam@example.com"])

    assert assert_remote_entities_safe([pseudo, str(pseudo)]) == [str(pseudo), str(pseudo)]
