"""HMAC-backed entity resolver with local anchor unification.

Contact identity mappings stay private/local. Remote surfaces must only ever see
opaque ``PERSON_*`` tokens produced here.
"""

from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Iterable
from uuid import uuid4

from personal_enigma.domain import PrivatePerson, PrivatePersonRef
from personal_enigma.identity.resolver import Pseudonym

PERSON_PSEUDONYM_PREFIX = "PERSON_"
_PERSON_TOKEN_RE = re.compile(rf"^{re.escape(PERSON_PSEUDONYM_PREFIX)}[0-9A-F]{{6}}$")


class HmacEntityResolver:
    """Unify email / calendar invite name / contact anchors → stable PERSON_*.

    Anchors observed together on a ``PrivatePerson`` (or via ``index``) are
    unioned so later ``resolve_ref`` calls that share any anchor return the same
    pseudonym.
    """

    def __init__(self, key: bytes | str) -> None:
        if isinstance(key, str):
            if not key:
                raise ValueError("HmacEntityResolver key must be non-empty")
            self._key = key.encode("utf-8")
        else:
            if not key:
                raise ValueError("HmacEntityResolver key must be non-empty")
            self._key = key
        self._anchor_to_entity: dict[str, str] = {}
        self._entity_canonical: dict[str, str] = {}

    def index(self, people: Iterable[PrivatePerson]) -> None:
        """Ingest Contacts (or other local) people so refs can unify against them."""
        for person in people:
            self.resolve_person(person)

    def resolve_person(self, person: PrivatePerson) -> Pseudonym:
        anchors = self._anchors_from_person(person)
        if not anchors:
            anchors = [f"uuid:{person.id}"]
        entity_id = self._unify(anchors)
        return self._pseudonym_for_entity(entity_id)

    def resolve_ref(self, ref: PrivatePersonRef) -> Pseudonym | None:
        anchors = self._anchors_from_ref(ref)
        if not anchors:
            return None
        entity_id = self._unify(anchors)
        return self._pseudonym_for_entity(entity_id)

    def _unify(self, anchors: list[str]) -> str:
        existing: list[str] = []
        for anchor in anchors:
            entity = self._anchor_to_entity.get(anchor)
            if entity is not None and entity not in existing:
                existing.append(entity)

        if existing:
            survivor = sorted(existing)[0]
            for entity in existing:
                if entity == survivor:
                    continue
                self._merge_entity(entity, survivor)
        else:
            survivor = self._new_entity_id(anchors)

        if survivor not in self._entity_canonical:
            self._entity_canonical[survivor] = anchors[0]

        for anchor in anchors:
            self._anchor_to_entity[anchor] = survivor
        return survivor

    def _merge_entity(self, source: str, target: str) -> None:
        for anchor, entity in list(self._anchor_to_entity.items()):
            if entity == source:
                self._anchor_to_entity[anchor] = target
        canonical = self._entity_canonical.pop(source, None)
        if canonical is not None and target not in self._entity_canonical:
            self._entity_canonical[target] = canonical

    def _new_entity_id(self, anchors: list[str]) -> str:
        for anchor in anchors:
            if anchor.startswith("email:") or anchor.startswith("provider:"):
                return f"ent:{anchor}"
        return f"ent:{uuid4()}"

    def _pseudonym_for_entity(self, entity_id: str) -> Pseudonym:
        material = self._entity_canonical.get(entity_id, entity_id)
        digest = hmac.new(self._key, material.encode("utf-8"), hashlib.sha256).hexdigest()
        return Pseudonym(value=f"{PERSON_PSEUDONYM_PREFIX}{digest[:6].upper()}")

    @staticmethod
    def _anchors_from_person(person: PrivatePerson) -> list[str]:
        anchors: list[str] = []
        for email in person.email_addresses:
            normalised = _normalise_email(email)
            if normalised:
                anchors.append(f"email:{normalised}")
        for phone in person.phone_numbers:
            normalised = _normalise_phone(phone)
            if normalised:
                anchors.append(f"phone:{normalised}")
        if person.display_name:
            name = _normalise_name(person.display_name)
            if name:
                anchors.append(f"name:{name}")
        for alias in person.aliases:
            name = _normalise_name(alias)
            if name:
                anchors.append(f"name:{name}")
        for provider, pid in sorted(person.provider_ids.items()):
            if pid and pid.strip():
                anchors.append(f"provider:{provider}:{pid.strip()}")
        seen: set[str] = set()
        ordered: list[str] = []
        for anchor in anchors:
            if anchor not in seen:
                seen.add(anchor)
                ordered.append(anchor)
        return ordered

    @staticmethod
    def _anchors_from_ref(ref: PrivatePersonRef) -> list[str]:
        anchors: list[str] = []
        if ref.email:
            normalised = _normalise_email(ref.email)
            if normalised:
                anchors.append(f"email:{normalised}")
        if ref.provider_id and ref.provider_id.strip():
            anchors.append(f"provider:ref:{ref.provider_id.strip()}")
        if ref.display_name:
            name = _normalise_name(ref.display_name)
            if name:
                anchors.append(f"name:{name}")
        return anchors


def is_person_pseudonym(value: str) -> bool:
    """Return True when ``value`` is an opaque PERSON_* token."""
    return bool(_PERSON_TOKEN_RE.fullmatch(value))


def assert_remote_entities_safe(entities: Iterable[object]) -> list[str]:
    """Reject raw ``PrivatePerson`` (or other non-pseudonym) values for remote payloads.

    Contact identity mappings remain local; only ``PERSON_*`` tokens may leave the box.
    """
    safe: list[str] = []
    for entity in entities:
        if isinstance(entity, PrivatePerson):
            raise ValueError(
                "Raw PrivatePerson must not appear in remote payloads; use PERSON_* pseudonyms"
            )
        if isinstance(entity, Pseudonym):
            token = str(entity)
        elif isinstance(entity, str):
            token = entity
        else:
            raise ValueError(f"Unsupported remote entity type: {type(entity)!r}")
        if not is_person_pseudonym(token):
            raise ValueError(f"Remote entity must be opaque PERSON_* token, got {token!r}")
        safe.append(token)
    return safe


def _normalise_email(value: str) -> str | None:
    cleaned = value.strip().lower()
    return cleaned or None


def _normalise_name(value: str) -> str | None:
    cleaned = " ".join(value.strip().lower().split())
    return cleaned or None


def _normalise_phone(value: str) -> str | None:
    digits = re.sub(r"\D+", "", value)
    return digits or None
