"""Deterministic semantic-preservation tests (R-L09)."""

from __future__ import annotations

from personal_enigma.transformation.protocol import TransformedContext
from personal_enigma.transformation.semantic_preservation import (
    SemanticPreservationExpectation,
    assert_semantic_preservation,
    blocker_resolved_relation,
)


def test_identity_removed_dependency_preserved() -> None:
    ctx = TransformedContext(
        summary="PERSON_B supplied RESOURCE_C for TASK_A",
        entities=["TASK_A", "RESOURCE_C", "PERSON_B"],
        relations=[
            blocker_resolved_relation(
                task_subject="TASK_A",
                resource_object="RESOURCE_C",
                resolved_by="PERSON_B",
                resolved_at="DATE_T0",
            )
        ],
        may_transmit_remotely=True,
    )
    result = assert_semantic_preservation(
        ctx,
        SemanticPreservationExpectation(
            must_not_contain=("alex", "jordan", "@"),
            required_relation_types=("BLOCKED_BY",),
            required_relation_subjects=("TASK_A",),
            min_relations=1,
        ),
    )
    assert result.passed


def test_identity_leak_fails() -> None:
    ctx = TransformedContext(
        summary="Jordan sent Alex the link",
        entities=[],
        relations=[],
        may_transmit_remotely=True,
    )
    result = assert_semantic_preservation(
        ctx,
        SemanticPreservationExpectation(
            must_not_contain=("alex", "jordan"),
            identity_check_scope="full",
        ),
    )
    assert not result.passed
    assert any("identity leak" in v for v in result.violations)


def test_blocker_resolved_relation_shape() -> None:
    rel = blocker_resolved_relation(
        task_subject="TASK_A",
        resource_object="RESOURCE_B",
        resolved_by="PERSON_C",
        resolved_at="DATE_T0",
    )
    assert rel.type == "BLOCKED_BY"
    assert rel.state == "resolved"
    assert rel.causal == "resource_supplied_unblocks_task"
