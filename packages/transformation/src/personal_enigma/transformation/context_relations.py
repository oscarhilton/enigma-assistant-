"""Attach privacy-safe relations to an existing TransformedContext."""

from __future__ import annotations

from personal_enigma.transformation.protocol import TransformedContext
from personal_enigma.transformation.relations import SemanticRelation, merge_relations


def with_relations(
    ctx: TransformedContext,
    *extra: list[SemanticRelation],
) -> TransformedContext:
    """Return a copy of *ctx* with additional deduped relations."""
    groups = [ctx.relations, *extra]
    return ctx.model_copy(update={"relations": merge_relations(*groups)})


__all__ = ["with_relations"]
