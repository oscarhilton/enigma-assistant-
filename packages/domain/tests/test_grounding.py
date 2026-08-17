from personal_enigma.domain import (
    AssertionChallenge,
    AssertionEgressClass,
    AssertionKind,
    AssertionSensitivity,
    ChallengeDisposition,
    EpistemicStatus,
    EvidenceUnknown,
    GroundedAssertion,
    RetentionClass,
    UnknownReason,
)


def test_grounded_assertion_roundtrip() -> None:
    assertion = GroundedAssertion(
        id="assertion_1",
        kind=AssertionKind.FACT,
        subject="calendar",
        predicate="has_items",
        value=False,
        epistemic_status=EpistemicStatus.SYSTEM_VERIFIED,
        evidence_refs=["cal_1"],
        purpose_tags=["coverage", "planning"],
        retention_class=RetentionClass.EPHEMERAL_ANSWER_ONLY,
        egress_class=AssertionEgressClass.REMOTE_SAFE,
        sensitivity=AssertionSensitivity.PERSONAL,
    )

    restored = GroundedAssertion.model_validate(assertion.model_dump())
    assert restored.epistemic_status == EpistemicStatus.SYSTEM_VERIFIED
    assert restored.value is False
    assert restored.retention_class == RetentionClass.EPHEMERAL_ANSWER_ONLY


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
        subject="question",
        predicate="monday_free",
        disposition=ChallengeDisposition.QUALIFIES,
        summary="Bank holiday status is useful but does not establish whether the user is off.",
        evidence_refs=["holiday_1"],
    )

    restored = AssertionChallenge.model_validate(challenge.model_dump())
    assert restored.disposition == ChallengeDisposition.QUALIFIES
    assert restored.evidence_refs == ["holiday_1"]
