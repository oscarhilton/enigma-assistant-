"""Deterministic semantic-preservation checks for transforms (R-L09).

Independent of any LLM — verifies that task-relevant relations survive
privacy transformation while identity is removed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from personal_enigma.transformation.protocol import TransformedContext
from personal_enigma.transformation.relations import SemanticRelation


@dataclass(frozen=True, slots=True)
class SemanticPreservationExpectation:
    """Expected properties after transform (no raw identity)."""

    must_not_contain: tuple[str, ...] = ()
    required_relation_types: tuple[str, ...] = ()
    required_relation_subjects: tuple[str, ...] = ()
    min_relations: int = 0
    identity_check_scope: Literal["full", "relations_entities"] = "relations_entities"
    require_resolved_blockers: tuple[str, ...] = ()


@dataclass
class SemanticPreservationResult:
    passed: bool
    violations: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {"passed": self.passed, "violations": self.violations}


def assert_semantic_preservation(
    ctx: TransformedContext,
    expectation: SemanticPreservationExpectation,
) -> SemanticPreservationResult:
    """Check transform output against deterministic semantic expectations."""
    if expectation.identity_check_scope == "full":
        blob = ctx.summary + " " + " ".join(ctx.entities)
    else:
        blob = " ".join(ctx.entities)
    for rel in ctx.relations:
        blob += " " + rel.model_dump_json()
    violations: list[str] = []
    for forbidden in expectation.must_not_contain:
        if forbidden.lower() in blob.lower():
            violations.append(f"identity leak: {forbidden!r}")
    if len(ctx.relations) < expectation.min_relations:
        violations.append(
            f"expected >= {expectation.min_relations} relations, got {len(ctx.relations)}"
        )
    rel_types = {r.type for r in ctx.relations}
    for required in expectation.required_relation_types:
        if required not in rel_types:
            violations.append(f"missing relation type: {required}")
    rel_subjects = {r.subject for r in ctx.relations}
    for required in expectation.required_relation_subjects:
        if required not in rel_subjects:
            violations.append(f"missing relation subject: {required}")
    for task in expectation.require_resolved_blockers:
        blocked = [
            r
            for r in ctx.relations
            if r.subject == task and r.type == "BLOCKED_BY" and r.state == "resolved"
        ]
        if not blocked:
            violations.append(f"missing resolved BLOCKED_BY for {task}")
        elif not any(r.causal and "actionable" in r.causal.lower() for r in blocked):
            violations.append(f"missing causal actionability for {task}")
    return SemanticPreservationResult(passed=not violations, violations=violations)


def blocker_resolved_relation(
    *,
    task_subject: str,
    resource_object: str,
    resolved_by: str,
    resolved_at: str,
) -> SemanticRelation:
    """General pattern: external resource unblocked a waiting task."""
    return SemanticRelation(
        type="BLOCKED_BY",
        subject=task_subject,
        object=resource_object,
        state="resolved",
        resolved_by=resolved_by,
        resolved_at=resolved_at,
        causal="resource_supplied_unblocks_task",
    )


__all__ = [
    "SemanticPreservationExpectation",
    "SemanticPreservationResult",
    "assert_semantic_preservation",
    "blocker_resolved_relation",
]
