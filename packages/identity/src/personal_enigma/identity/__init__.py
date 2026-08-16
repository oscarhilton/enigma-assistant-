"""Local identity resolution — never expose PrivatePerson remotely."""

from personal_enigma.identity.hmac_resolver import (
    PERSON_PSEUDONYM_PREFIX,
    HmacEntityResolver,
    assert_remote_entities_safe,
    is_person_pseudonym,
)
from personal_enigma.identity.resolver import EntityResolver, Pseudonym

__all__ = [
    "PERSON_PSEUDONYM_PREFIX",
    "EntityResolver",
    "HmacEntityResolver",
    "Pseudonym",
    "assert_remote_entities_safe",
    "is_person_pseudonym",
]
