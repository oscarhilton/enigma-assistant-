"""C29 freeze-scenario tests — retention gate at API package boundary."""

from __future__ import annotations

from datetime import UTC, datetime

from personal_enigma.domain.durable_assertions import InMemoryDurableAssertionStore
from personal_enigma.domain.grounding import (
    AssertionKind,
    AssertionValidityKind,
    EpistemicStatus,
    GroundedAssertion,
)
from personal_enigma.domain.retention_gate import RetentionOutcome, evaluate_retention


def _freeze_assertion(**overrides: object) -> GroundedAssertion:
    base: dict[str, object] = {
        "id": "freeze-1",
        "kind": AssertionKind.PREFERENCE,
        "subject": "self",
        "predicate": "likes",
        "value": "ceramics",
        "epistemic_status": EpistemicStatus.USER_CONFIRMED,
        "purpose_tags": ["user_explicit_recall"],
    }
    base.update(overrides)
    return GroundedAssertion.model_validate(base)


def test_freeze_ceramics_gate() -> None:
    confirmed = evaluate_retention(_freeze_assertion())
    inferred = evaluate_retention(
        _freeze_assertion(
            id="freeze-2",
            epistemic_status=EpistemicStatus.MODEL_INFERRED,
        )
    )
    assert confirmed.outcome == RetentionOutcome.DURABLE
    assert inferred.outcome == RetentionOutcome.EPHEMERAL


def test_freeze_detective_not_dossier() -> None:
    decisions = [
        evaluate_retention(
            _freeze_assertion(
                id="maya-bday",
                subject="PERSON_Maya",
                predicate="birthday",
                value="March 12",
                kind=AssertionKind.FACT,
                purpose_tags=[],
            )
        ),
        evaluate_retention(
            _freeze_assertion(
                id="maya-profile",
                subject="PERSON_Maya",
                predicate="personality_type",
                value="anxious achiever",
                kind=AssertionKind.HYPOTHESIS,
                epistemic_status=EpistemicStatus.MODEL_INFERRED,
                purpose_tags=[],
            )
        ),
    ]
    assert decisions[0].outcome == RetentionOutcome.DURABLE
    assert decisions[1].outcome in (RetentionOutcome.REJECT, RetentionOutcome.EPHEMERAL)


def test_freeze_forget_cascade() -> None:
    store = InMemoryDurableAssertionStore()
    root = _freeze_assertion(id="root", predicate="gift_history", value="2024 mug")
    decision = evaluate_retention(root)
    store.store(root, decision)
    result = store.forget("root")
    assert "root" in result.deleted_assertion_ids
    assert store.list_retained_ids() == []


def test_freeze_third_party_concrete_vs_profiling() -> None:
    concrete = evaluate_retention(
        _freeze_assertion(
            subject="PERSON_Maya",
            predicate="likes",
            value="ceramics",
        )
    )
    profiling = evaluate_retention(
        _freeze_assertion(
            id="profiling",
            subject="PERSON_Maya",
            predicate="is_emotionally_dependent_on",
            value="Oscar",
        )
    )
    assert concrete.outcome == RetentionOutcome.DURABLE
    assert profiling.outcome == RetentionOutcome.REJECT


def test_freeze_purpose_expiry() -> None:
    decision = evaluate_retention(
        _freeze_assertion(
            predicate="gift_history",
            purpose_tags=["temporary_case"],
            validity_kind=AssertionValidityKind.TTL,
            temporal_scope="gift_planning_2026",
            valid_until=datetime(2026, 6, 1, tzinfo=UTC),
        )
    )
    assert decision.outcome == RetentionOutcome.TTL
    assert decision.outcome != RetentionOutcome.DURABLE
