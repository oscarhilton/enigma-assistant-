"""C26 — response-grounding bridge over frozen GroundedAssertion v1."""

from __future__ import annotations

from datetime import UTC, datetime

from personal_enigma.api.conversation_context import ConversationContext
from personal_enigma.api.evidence_bundle import EvidenceBundle, FetchMission, build_evidence_bundle
from personal_enigma.api.respond_grounding import (
    apply_respond_grounding_fence,
    has_verified_bundle_evidence,
    seek_source_evidence_covered,
    violates_bundle_conflict_resolution,
    violates_dialogue_fossil_as_fact,
    violates_superseded_assertion_as_current,
)
from personal_enigma.domain import (
    AssertionValidityKind,
    DerivationKind,
    EpistemicStatus,
    GroundedAssertion,
)


def _bundle(**overrides: object) -> EvidenceBundle:
    base = EvidenceBundle(
        mission=FetchMission(question="test", authority="READ"),
        coverage_adequate=False,
        courier_state="partially_returned",
    )
    return base.model_copy(update=overrides)


def _fossil() -> GroundedAssertion:
    return GroundedAssertion(
        id="assistant_fossil",
        subject="person_b",
        predicate="likes_ceramics",
        value="ceramics",
        epistemic_status=EpistemicStatus.MODEL_INFERRED,
        derivation_kind=DerivationKind.DIALOGUE_HISTORY,
    )


def test_fossil_presented_as_fact_is_fenced() -> None:
    bundle = _bundle(grounded_assertions=[_fossil()])
    text = "Person B is really into ceramics."
    assert violates_dialogue_fossil_as_fact(text, bundle)
    fenced = apply_respond_grounding_fence(
        text,
        context=ConversationContext(),
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
        evidence_bundle=bundle,
    )
    assert seek_source_evidence_covered(fenced)


def test_hedged_fossil_recall_is_allowed() -> None:
    bundle = _bundle(grounded_assertions=[_fossil()])
    hedged = (
        "From our conversation, ceramics came up for Person B, "
        "but I don't have verified details."
    )
    assert not violates_dialogue_fossil_as_fact(hedged, bundle)
    assert apply_respond_grounding_fence(
        hedged,
        context=ConversationContext(),
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
        evidence_bundle=bundle,
    ) == hedged


def test_verified_assertion_counts_as_support() -> None:
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    bundle = _bundle(
        grounded_assertions=[
            GroundedAssertion(
                id="attention_count",
                subject="attention",
                predicate="needs_you_count",
                value=2,
                epistemic_status=EpistemicStatus.SYSTEM_VERIFIED,
                evidence_refs=["need_1", "need_2"],
                validity_kind=AssertionValidityKind.SOURCE_LIFETIME,
            )
        ],
    )
    assert has_verified_bundle_evidence(tool_results=None, evidence_bundle=bundle, now=now)


def test_fossil_does_not_count_as_verified_support() -> None:
    bundle = _bundle(grounded_assertions=[_fossil()])
    assert not has_verified_bundle_evidence(tool_results=None, evidence_bundle=bundle)


def test_conflict_resolution_without_ack_is_fenced() -> None:
    bundle = build_evidence_bundle(
        question="am i working monday?",
        working_set={
            "request_kind": "subject_details",
            "scope": "work",
            "authority": "READ",
            "fetch_mission": {"planned_tools": ["world.explain"]},
            "capability_contract": {"allowed": ["world.explain"], "unavailable": []},
        },
        tool_results=[
            {
                "name": "world.explain",
                "ok": True,
                "data": {
                    "grounded_assertions": [
                        {
                            "id": "works_yes",
                            "subject": "user",
                            "predicate": "works_monday",
                            "value": True,
                            "temporal_scope": "2026-08-17",
                            "epistemic_status": "user_confirmed",
                        },
                        {
                            "id": "works_no",
                            "subject": "user",
                            "predicate": "works_monday",
                            "value": False,
                            "temporal_scope": "2026-08-17",
                            "epistemic_status": "externally_verified",
                        },
                    ]
                },
            }
        ],
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
    )
    assert bundle.conflicts
    definitive = "You are working on Monday."
    assert violates_bundle_conflict_resolution(definitive, bundle)
    fenced = apply_respond_grounding_fence(
        definitive,
        context=ConversationContext(),
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
        evidence_bundle=bundle,
    )
    assert "conflicting" in fenced.casefold()


def test_conflict_acknowledgement_is_allowed() -> None:
    bundle = build_evidence_bundle(
        question="am i working monday?",
        working_set={
            "request_kind": "subject_details",
            "scope": "work",
            "authority": "READ",
            "fetch_mission": {"planned_tools": ["world.explain"]},
            "capability_contract": {"allowed": ["world.explain"], "unavailable": []},
        },
        tool_results=[
            {
                "name": "world.explain",
                "ok": True,
                "data": {
                    "grounded_assertions": [
                        {
                            "id": "works_yes",
                            "subject": "user",
                            "predicate": "works_monday",
                            "value": True,
                            "temporal_scope": "2026-08-17",
                            "epistemic_status": "user_confirmed",
                        },
                        {
                            "id": "works_no",
                            "subject": "user",
                            "predicate": "works_monday",
                            "value": False,
                            "temporal_scope": "2026-08-17",
                            "epistemic_status": "externally_verified",
                        },
                    ]
                },
            }
        ],
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
    )
    hedged = (
        "I have conflicting information about whether you're working Monday — "
        "I need to check before stating it as settled."
    )
    assert not violates_bundle_conflict_resolution(hedged, bundle)


def test_superseded_assertion_restated_as_current_is_fenced() -> None:
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    bundle = _bundle(
        grounded_assertions=[
            GroundedAssertion(
                id="old_time",
                subject="brunch",
                predicate="start_time",
                value="10:00",
                epistemic_status=EpistemicStatus.USER_REPORTED,
            ),
            GroundedAssertion(
                id="new_time",
                subject="brunch",
                predicate="start_time",
                value="11:00",
                epistemic_status=EpistemicStatus.USER_CONFIRMED,
                supersedes=["old_time"],
            ),
        ],
    )
    stale_claim = "Brunch is at 10:00."
    assert violates_superseded_assertion_as_current(stale_claim, bundle, now=now)
    fenced = apply_respond_grounding_fence(
        stale_claim,
        context=ConversationContext(),
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
        evidence_bundle=bundle,
    )
    assert fenced != stale_claim


def test_current_assertion_value_is_allowed() -> None:
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    bundle = _bundle(
        grounded_assertions=[
            GroundedAssertion(
                id="new_time",
                subject="brunch",
                predicate="start_time",
                value="11:00",
                epistemic_status=EpistemicStatus.USER_CONFIRMED,
                supersedes=["old_time"],
            ),
        ],
    )
    current_claim = "Brunch is at 11:00."
    assert not violates_superseded_assertion_as_current(current_claim, bundle, now=now)
    assert not violates_dialogue_fossil_as_fact(current_claim, bundle, now=now)
