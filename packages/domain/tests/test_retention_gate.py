"""C29 retention gate unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

from personal_enigma.domain.durable_assertions import InMemoryDurableAssertionStore
from personal_enigma.domain.grounding import (
    AssertionKind,
    AssertionValidityKind,
    DerivationKind,
    EpistemicStatus,
    GroundedAssertion,
)
from personal_enigma.domain.retention import RetentionClass, RetentionPurpose
from personal_enigma.domain.retention_gate import (
    RetentionOutcome,
    RetentionRejectionReason,
    evaluate_retention,
)


def _assertion(**overrides: object) -> GroundedAssertion:
    base: dict[str, object] = {
        "id": "A1",
        "kind": AssertionKind.FACT,
        "subject": "self",
        "predicate": "likes",
        "value": "ceramics",
        "epistemic_status": EpistemicStatus.USER_CONFIRMED,
        "purpose_tags": ["user_explicit_recall"],
        "evidence_refs": ["EV1"],
    }
    base.update(overrides)
    return GroundedAssertion.model_validate(base)


def test_ceramics_confirmed_preference_may_become_durable() -> None:
    decision = evaluate_retention(_assertion())
    assert decision.outcome == RetentionOutcome.DURABLE
    assert decision.retention_class == RetentionClass.DURABLE_SHADOW
    assert decision.purpose == RetentionPurpose.USER_EXPLICIT_RECALL


def test_ceramics_inferred_preference_stays_ephemeral() -> None:
    decision = evaluate_retention(
        _assertion(
            epistemic_status=EpistemicStatus.MODEL_INFERRED,
            derivation_kind=DerivationKind.INFERENCE,
        )
    )
    assert decision.outcome == RetentionOutcome.EPHEMERAL
    assert decision.rejection_reason == RetentionRejectionReason.INFERENCE_NOT_DURABLE


def test_detective_rich_source_yields_concrete_facts_not_dossier() -> None:
    rich_material = [
        _assertion(
            id="fact-birthday",
            subject="PERSON_Maya",
            predicate="birthday",
            value="March 12",
            epistemic_status=EpistemicStatus.SOURCE_OBSERVED,
            purpose_tags=[],
        ),
        _assertion(
            id="pattern-commute",
            subject="PERSON_Maya",
            predicate="behavioural_pattern",
            value="leaves office late on Thursdays",
            kind=AssertionKind.PATTERN,
            epistemic_status=EpistemicStatus.SOURCE_OBSERVED,
            purpose_tags=[],
        ),
        _assertion(
            id="hypothesis-stress",
            subject="PERSON_Maya",
            predicate="psychological_state",
            value="under work stress",
            kind=AssertionKind.HYPOTHESIS,
            epistemic_status=EpistemicStatus.MODEL_INFERRED,
            purpose_tags=[],
        ),
    ]
    decisions = [evaluate_retention(row) for row in rich_material]
    assert decisions[0].outcome == RetentionOutcome.DURABLE
    assert decisions[1].outcome == RetentionOutcome.EPHEMERAL
    assert decisions[2].outcome == RetentionOutcome.EPHEMERAL


def test_forget_invalidates_unjustified_derivatives() -> None:
    store = InMemoryDurableAssertionStore()
    parent = _assertion(id="parent-fact", predicate="gift_history", value="mug 2024")
    parent_decision = evaluate_retention(parent)
    assert parent_decision.outcome == RetentionOutcome.DURABLE
    store.store(parent, parent_decision)

    summary = _assertion(
        id="derived-summary",
        kind=AssertionKind.PATTERN,
        predicate="convention",
        value="usually gifts ceramics",
        epistemic_status=EpistemicStatus.DETERMINISTICALLY_DERIVED,
        derived_from=["parent-fact"],
        purpose_tags=["temporary_case"],
        validity_kind=AssertionValidityKind.DERIVED_LIFETIME,
        temporal_scope="gift_planning_2026",
    )
    summary_decision = evaluate_retention(summary)
    assert summary_decision.outcome == RetentionOutcome.EPHEMERAL
    # Derived summaries stay ephemeral at the gate; store only durable parents in this slice.
    cascade = store.forget("parent-fact")
    assert cascade.deleted_assertion_ids == ["parent-fact"]
    assert store.list_retained_ids() == []


def test_third_party_ceramics_ok_profiling_rejected() -> None:
    ok = evaluate_retention(
        _assertion(
            subject="PERSON_Maya",
            predicate="likes",
            value="ceramics",
            kind=AssertionKind.PREFERENCE,
            epistemic_status=EpistemicStatus.USER_CONFIRMED,
            purpose_tags=["user_explicit_recall"],
        )
    )
    rejected = evaluate_retention(
        _assertion(
            id="A2",
            subject="PERSON_Maya",
            predicate="is_emotionally_dependent_on",
            value="Oscar",
            epistemic_status=EpistemicStatus.USER_CONFIRMED,
            purpose_tags=["user_explicit_recall"],
        )
    )
    assert ok.outcome == RetentionOutcome.DURABLE
    assert rejected.outcome == RetentionOutcome.REJECT
    assert rejected.rejection_reason == RetentionRejectionReason.THIRD_PARTY_PROFILING


def test_purpose_expiry_temporary_case_is_ttl_not_durable_forever() -> None:
    decision = evaluate_retention(
        _assertion(
            predicate="gift_history",
            value="planned mug",
            purpose_tags=["temporary_case", "gift_planning"],
            validity_kind=AssertionValidityKind.TTL,
            temporal_scope="gift_planning_2026",
            valid_until=datetime(2026, 12, 31, tzinfo=UTC),
        )
    )
    assert decision.outcome == RetentionOutcome.TTL
    assert decision.retention_class == RetentionClass.ACTIVE_UNTIL_RESOLVED
    assert decision.lifetime is not None
