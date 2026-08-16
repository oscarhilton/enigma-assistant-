"""Stub HMAC entity resolver for use until M10 ships Contacts-backed identity."""

from __future__ import annotations

import hashlib
import hmac

from personal_enigma.domain import PrivatePerson, PrivatePersonRef
from personal_enigma.identity import Pseudonym


class StubHmacResolver:
    """Deterministic PERSON_* pseudonyms from a fixed HMAC key.

    Satisfies the ``EntityResolver`` protocol without depending on Contacts.
    Stable for a given key + anchor material — suitable for golden tests.
    """

    def __init__(self, key: bytes | str = b"enigma-stub-hmac-key") -> None:
        self._key = key.encode("utf-8") if isinstance(key, str) else key

    def resolve_person(self, person: PrivatePerson) -> Pseudonym:
        anchors: list[str] = []
        anchors.extend(e.strip().lower() for e in person.email_addresses if e.strip())
        anchors.extend(p.strip() for p in person.phone_numbers if p.strip())
        if person.display_name and person.display_name.strip():
            anchors.append(person.display_name.strip().lower())
        anchors.extend(a.strip().lower() for a in person.aliases if a.strip())
        for provider, pid in sorted(person.provider_ids.items()):
            if pid.strip():
                anchors.append(f"{provider}:{pid.strip()}")
        if not anchors:
            anchors.append(str(person.id))
        return self._pseudonym("|".join(anchors))

    def resolve_ref(self, ref: PrivatePersonRef) -> Pseudonym | None:
        if ref.email and ref.email.strip():
            return self._pseudonym(ref.email.strip().lower())
        if ref.provider_id and ref.provider_id.strip():
            return self._pseudonym(f"provider:{ref.provider_id.strip()}")
        if ref.display_name and ref.display_name.strip():
            return self._pseudonym(ref.display_name.strip().lower())
        return None

    def _pseudonym(self, material: str) -> Pseudonym:
        digest = hmac.new(self._key, material.encode("utf-8"), hashlib.sha256).hexdigest()
        return Pseudonym(value=f"PERSON_{digest[:6].upper()}")
