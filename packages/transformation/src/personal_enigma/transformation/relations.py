"""Privacy-safe relational semantics for transformed context (R-L09)."""

from __future__ import annotations

from pydantic import BaseModel


class SemanticRelation(BaseModel):
    """A task-relevant relation with identity stripped to pseudonyms/tokens."""

    type: str
    subject: str
    object: str
    state: str | None = None
    resolved_by: str | None = None
    resolved_at: str | None = None
    since: str | None = None
    due: str | None = None
    causal: str | None = None


def merge_relations(*groups: list[SemanticRelation]) -> list[SemanticRelation]:
    """Dedupe relations by (type, subject, object)."""
    seen: set[tuple[str, str, str]] = set()
    out: list[SemanticRelation] = []
    for group in groups:
        for rel in group:
            key = (rel.type, rel.subject, rel.object)
            if key in seen:
                continue
            seen.add(key)
            out.append(rel)
    return out


def relation_to_dict(rel: SemanticRelation) -> dict[str, str | None]:
    return rel.model_dump(exclude_none=True)


__all__ = ["SemanticRelation", "merge_relations", "relation_to_dict"]
