"""Select first; transform second; transmit last."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from personal_enigma.transformation.relations import SemanticRelation


class TransformedContext(BaseModel):
    """Sanitised context safe to consider for remote reasoning."""

    summary: str
    entities: list[str] = Field(default_factory=list)
    relations: list[SemanticRelation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    may_transmit_remotely: bool = False


@runtime_checkable
class EnigmaTransformer(Protocol):
    """Transforms private records into Enigma domain context."""

    def transform(self, private_record: dict[str, Any]) -> TransformedContext:
        """Transform a private record without expanding remote visibility."""
        ...
