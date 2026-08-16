"""Entity resolver protocol (implemented in M10)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from personal_enigma.domain import PrivatePerson, PrivatePersonRef


class Pseudonym(BaseModel):
    """Opaque remote-safe person identifier."""

    value: str

    def __str__(self) -> str:
        return self.value


@runtime_checkable
class EntityResolver(Protocol):
    def resolve_person(self, person: PrivatePerson) -> Pseudonym:
        """Map a private contact record to a stable PERSON_* pseudonym."""
        ...

    def resolve_ref(self, ref: PrivatePersonRef) -> Pseudonym | None:
        """Resolve a lightweight person ref when possible."""
        ...
