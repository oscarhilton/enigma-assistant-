from datetime import UTC, datetime, timedelta

from personal_enigma.domain import (
    AssertionChallenge,
    AssertionEgressClass,
    AssertionKind,
    AssertionSensitivity,
    AssertionValidityKind,
    ChallengeDisposition,
    DerivationKind,
    EpistemicStatus,
    EvidenceUnknown,
    GroundedAssertion,
    RetentionClass,
    UnknownReason,
    classify_assertion_challenge,
    conflicting_assertion_ids,
    current_assertions,
    is_epistemic_transition_permitted,
)


def test_grounded_assertion_roundtrip() -> None:
    assertion = GroundedAssertion(
        id="assertion_1",
        kind=AssertionKind.FACT,
        subject="calendar",
        predicate="has_items",
        value=False,
        scope="work",
        epistemic_status=EpistemicStatus.SYSTEM_VERIFIED,
        evidence_refs=["cal_1"],
        validity_kind=AssertionValidityKind.SOURCE_LIFETIME,
        purpose_tags=["coverage", "planning"],
        retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
        egress_class=AssertionEgressClass.REMOTE_SAFE,
        sensitivity=AssertionSensitivity.PERSONAL,
    )

    restored = GroundedAssertion.model_validate(assertion.model_dump())
    assert restored.epistemic_status == EpistemicStatus.SYSTEM_VERIFIED
    assert restored.value is False
    assert restored.retention_class == RetentionClass.EPHEMERAL_ANSWER_ONLY
    assert restored.scope == "work"
    assert restored.validity_kind == AssertionValidityKind.SOURCE_LIFETIME


def test_unknown_reason_roundtrip() -> None:
    unknown = EvidenceUnknown(
        subject="question",
        predicate="work_schedule",
        reason=UnknownReason.MISSING_EVIDENCE,
        missing_sources=["calendar", "world_changes"],
    )

    restored = EvidenceUnknown.model_validate(unknown.model_dump())
    assert restored.reason == UnknownReason.MISSING_EVIDENCE
    assert restored.missing_sources == ["calendar", "world_changes"]


def test_challenge_disposition_roundtrip() -> None:
    challenge = AssertionChallenge(
        claim_id="claim_1",
        related_assertion_ids=["holiday_1"],
        subject="question",
        predicate="monday_free",
        disposition=ChallengeDisposition.QUALIFIES,
        summary="Bank holiday status is useful but does not establish whether the user is off.",
        evidence_refs=["holiday_1"],
    )

    restored = AssertionChallenge.model_validate(challenge.model_dump())
    assert restored.disposition == ChallengeDisposition.QUALIFIES
    assert restored.evidence_refs == ["holiday_1"]
    assert restored.claim_id == "claim_1"
    assert restored.related_assertion_ids == ["holiday_1"]


def test_proposition_identity_requires_semantic_shape_match() -> None:
    first = GroundedAssertion(
        id="dog_species",
        subject="fido",
        predicate="species",
        value="dog",
        scope="biography",
        epistemic_status=EpistemicStatus.SOURCE_OBSERVED,
    )
    second = GroundedAssertion(
        id="dog_species_copy",
        subject="fido",
        predicate="species",
        value="dog",
        scope="biography",
        epistemic_status=EpistemicStatus.USER_CONFIRMED,
    )
    different = GroundedAssertion(
        id="mammal_species",
        subject="fido",
        predicate="species",
        value="mammal",
        scope="biography",
        epistemic_status=EpistemicStatus.DETERMINISTICALLY_DERIVED,
        derivation_kind=DerivationKind.DETERMINISTIC_RULE,
        derived_from=["dog_species"],
        validity_kind=AssertionValidityKind.DERIVED_LIFETIME,
    )

    assert first.refers_to_same_proposition(second) is True
    assert first.refers_to_same_proposition(different) is False


def test_ttl_assertion_becomes_stale_after_expiry() -> None:
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    assertion = GroundedAssertion(
        id="forecast_now",
        subject="weather",
        predicate="rain_expected",
        value=True,
        epistemic_status=EpistemicStatus.EXTERNALLY_VERIFIED,
        validity_kind=AssertionValidityKind.TTL,
        valid_until=now - timedelta(minutes=1),
    )

    assert assertion.is_usable_now(now=now) is False


def test_until_event_and_source_lifetime_assertions_expire_when_basis_breaks() -> None:
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    until_event = GroundedAssertion(
        id="office_closed_until_reopened",
        subject="office",
        predicate="closed",
        value=True,
        epistemic_status=EpistemicStatus.SOURCE_OBSERVED,
        validity_kind=AssertionValidityKind.UNTIL_EVENT,
        invalidated_by=["office_reopened"],
    )
    source_lifetime = GroundedAssertion(
        id="calendar_empty_today",
        subject="calendar",
        predicate="has_items",
        value=False,
        epistemic_status=EpistemicStatus.SYSTEM_VERIFIED,
        evidence_refs=["calendar_snapshot_1"],
        validity_kind=AssertionValidityKind.SOURCE_LIFETIME,
    )

    assert (
        until_event.is_usable_now(
            now=now,
            invalidating_assertion_ids={"office_reopened"},
        )
        is False
    )
    assert source_lifetime.is_usable_now(now=now, active_source_refs={"other_snapshot"}) is False


def test_conflicts_are_preserved_and_supersession_only_hides_superseded_claim() -> None:
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    original = GroundedAssertion(
        id="works_monday_user",
        subject="user",
        predicate="works_monday",
        value=True,
        epistemic_status=EpistemicStatus.USER_REPORTED,
    )
    refined = GroundedAssertion(
        id="works_monday_verified",
        subject="user",
        predicate="works_monday",
        value=True,
        epistemic_status=EpistemicStatus.SOURCE_OBSERVED,
        supersedes=["works_monday_user"],
    )
    conflicting = GroundedAssertion(
        id="works_monday_contractor",
        subject="user",
        predicate="works_monday",
        value=False,
        epistemic_status=EpistemicStatus.SOURCE_OBSERVED,
    )

    assert conflicting_assertion_ids([original, refined, conflicting]) == [
        ("works_monday_user", "works_monday_contractor"),
        ("works_monday_verified", "works_monday_contractor"),
    ]

    projected_ids = {
        assertion.id
        for assertion in current_assertions([original, refined, conflicting], now=now)
    }
    assert projected_ids == {"works_monday_verified", "works_monday_contractor"}


def test_challenge_classification_distinguishes_confirm_qualify_conflict_and_unresolved() -> None:
    claim = GroundedAssertion(
        id="claim",
        subject="user",
        predicate="works_monday",
        value=True,
        temporal_scope="2026-08-17",
        epistemic_status=EpistemicStatus.USER_CONFIRMED,
    )
    same = GroundedAssertion(
        id="same",
        subject="user",
        predicate="works_monday",
        value=True,
        temporal_scope="2026-08-17",
        epistemic_status=EpistemicStatus.SOURCE_OBSERVED,
    )
    conflict = GroundedAssertion(
        id="conflict",
        subject="user",
        predicate="works_monday",
        value=False,
        temporal_scope="2026-08-17",
        epistemic_status=EpistemicStatus.SOURCE_OBSERVED,
    )
    qualifier = GroundedAssertion(
        id="qualifier",
        subject="calendar",
        predicate="is_bank_holiday",
        value=True,
        temporal_scope="2026-08-17",
        epistemic_status=EpistemicStatus.EXTERNALLY_VERIFIED,
    )

    assert classify_assertion_challenge(claim, same) == ChallengeDisposition.CONFIRMS
    assert classify_assertion_challenge(claim, conflict) == ChallengeDisposition.CONFLICTS
    assert (
        classify_assertion_challenge(claim, qualifier, relevant_context=True)
        == ChallengeDisposition.QUALIFIES
    )
    assert (
        classify_assertion_challenge(claim, qualifier, unresolved=True)
        == ChallengeDisposition.DOES_NOT_ADDRESS
    )


def test_invalid_epistemic_promotion_paths_are_rejected() -> None:
    assert (
        is_epistemic_transition_permitted(
            target_status=EpistemicStatus.EXTERNALLY_VERIFIED,
            derivation_kind=DerivationKind.SEMANTIC_SIMILARITY,
            supporting_statuses=[EpistemicStatus.MODEL_INFERRED],
        )
        is False
    )
    assert (
        is_epistemic_transition_permitted(
            target_status=EpistemicStatus.USER_CONFIRMED,
            derivation_kind=DerivationKind.DIALOGUE_HISTORY,
            supporting_statuses=[EpistemicStatus.USER_REPORTED],
        )
        is False
    )
    assert (
        is_epistemic_transition_permitted(
            target_status=EpistemicStatus.DETERMINISTICALLY_DERIVED,
            derivation_kind=DerivationKind.DETERMINISTIC_RULE,
            supporting_statuses=[
                EpistemicStatus.SOURCE_OBSERVED,
                EpistemicStatus.EXTERNALLY_VERIFIED,
            ],
        )
        is True
    )
