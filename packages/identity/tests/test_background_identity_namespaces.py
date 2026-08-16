"""F-background-identity — email namespaces stay disjoint under Maya name collision."""

from __future__ import annotations

from uuid import uuid4

from personal_enigma.domain import PrivatePerson, PrivatePersonRef
from personal_enigma.identity import HmacEntityResolver, is_person_pseudonym

FIXED_KEY = b"f-background-identity-hmac-key"


def test_canonical_maya_and_background_maya_email_namespaces_differ() -> None:
    """Same display name must not collapse distinct email namespaces.

    Simulation assigns background people ``background-person-*`` / ``company-*.example``
    ids; identity resolution by email must yield different PERSON_* tokens than
    canonical Maya (``maya.chen@northwind.example``).
    """
    resolver = HmacEntityResolver(FIXED_KEY)

    canonical_maya = PrivatePerson(
        id=uuid4(),
        display_name="Maya Chen",
        email_addresses=["maya.chen@northwind.example"],
        provider_ids={"synthetic": "canonical-maya"},
    )
    background_maya = PrivatePerson(
        id=uuid4(),
        # Deliberate display-name collision with canonical Maya.
        display_name="Maya Chen",
        email_addresses=["person-4242@company-007.example"],
        provider_ids={"synthetic": "background-person-4242"},
    )

    # Resolve each contact on a fresh resolver so shared display-name anchors
    # are not unioned across people (email + provider namespaces stay primary).
    can_resolver = HmacEntityResolver(FIXED_KEY)
    bg_resolver = HmacEntityResolver(FIXED_KEY)
    can_pseudo = can_resolver.resolve_person(canonical_maya)
    bg_pseudo = bg_resolver.resolve_person(background_maya)
    assert is_person_pseudonym(str(can_pseudo))
    assert is_person_pseudonym(str(bg_pseudo))
    assert str(can_pseudo) != str(bg_pseudo)

    # Email-only refs on one resolver also stay distinct.
    by_email_can = resolver.resolve_ref(
        PrivatePersonRef(email="maya.chen@northwind.example")
    )
    by_email_bg = resolver.resolve_ref(
        PrivatePersonRef(email="person-4242@company-007.example")
    )
    assert by_email_can is not None
    assert by_email_bg is not None
    assert str(by_email_can) != str(by_email_bg)
    assert str(by_email_can) == str(can_pseudo)
    assert str(by_email_bg) == str(bg_pseudo)
