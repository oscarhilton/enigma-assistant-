"""C25 evidence bundle tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from personal_enigma.api.context_compilation import interpret_request
from personal_enigma.api.conversation_context import ConversationContext
from personal_enigma.api.evidence_bundle import (
    build_evidence_bundle,
    derive_courier_state,
    planned_tools_for_kind,
)
from personal_enigma.attention.projection import AttentionState
from personal_enigma.domain import (
    AssertionValidityKind,
    ChallengeDisposition,
    DerivationKind,
    EpistemicStatus,
    GroundedAssertion,
)


@dataclass
class _SessionStub:
    context: ConversationContext
    state: AttentionState = field(
        default_factory=lambda: AttentionState(simulated_time="2026-08-18T09:00:00Z")
    )


def _session() -> _SessionStub:
    return _SessionStub(context=ConversationContext())


def test_planned_tools_for_catch_up() -> None:
    tools = planned_tools_for_kind("catch_up")
    assert "attention.get_current" in tools
    assert "world.get_changes" in tools
    assert "agenda.get" in tools


def test_calendar_only_fetch_marks_coverage_inadequate_for_catch_up() -> None:
    bundle = build_evidence_bundle(
        question="what have i missed?",
        working_set={
            "request_kind": "catch_up",
            "scope": "work",
            "authority": "READ",
            "fetch_mission": {"planned_tools": planned_tools_for_kind("catch_up")},
            "capability_contract": {"allowed": ["agenda.get"], "unavailable": []},
        },
        tool_results=[
            {
                "name": "agenda.get",
                "ok": True,
                "data": {"period": "today", "empty_horizon": True, "calendar_evidence_ids": []},
            }
        ],
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
    )
    assert bundle.coverage_adequate is False
    assert "attention" in bundle.unsearched_sources
    assert derive_courier_state(bundle) == "partially_returned"
    assert any(
        assertion.subject == "calendar"
        and assertion.predicate == "has_items"
        and assertion.value is False
        for assertion in bundle.grounded_assertions
    )
    assert any(unknown.reason == "missing_evidence" for unknown in bundle.unknowns)
    assert any(challenge.disposition == "does_not_address" for challenge in bundle.challenges)


def test_what_should_i_be_doing_compiles_next_work() -> None:
    session = _session()
    interp = interpret_request("what should i be doing?", session)
    assert interp.request_kind == "next_work"
    assert interp.authority == "READ"


def test_catch_up_compiles_private_world() -> None:
    session = _session()
    interp = interpret_request("what have i missed?", session)
    assert interp.evidence_domain == "PRIVATE_WORLD"
    assert interp.request_kind == "catch_up"


def test_brunch_compiles_subject_details_with_personal_scope() -> None:
    session = _session()
    interp = interpret_request("what about the brunch", session)
    assert interp.request_kind == "subject_details"
    assert interp.constraints.scope == "personal"


def test_news_question_marks_blocked_bundle() -> None:
    bundle = build_evidence_bundle(
        question="the news?",
        working_set={
            "request_kind": None,
            "authority": "NONE",
            "capability_contract": {
                "allowed": [],
                "unavailable": ["arbitrary network"],
            },
        },
        tool_results=[],
        evidence_domain="GENERAL_KNOWLEDGE",
        authority="NONE",
    )
    assert "news" in bundle.unavailable_sources
    assert derive_courier_state(bundle) == "blocked"
    assert any(unknown.reason == "unavailable_capability" for unknown in bundle.unknowns)


def test_brunch_unresolved_when_no_subject() -> None:
    bundle = build_evidence_bundle(
        question="what about the brunch",
        working_set={
            "request_kind": "subject_details",
            "scope": "personal",
            "authority": "READ",
            "fetch_mission": {"planned_tools": planned_tools_for_kind("subject_details")},
            "capability_contract": {"allowed": ["world.explain"], "unavailable": []},
        },
        tool_results=[],
        current_subject_id=None,
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
    )
    assert "brunch" in bundle.unresolved_referents
    assert derive_courier_state(bundle) == "confused"
    assert any(unknown.reason == "unresolved_referent" for unknown in bundle.unknowns)


def test_attention_tool_produces_grounded_assertion() -> None:
    bundle = build_evidence_bundle(
        question="what should i be doing?",
        working_set={
            "request_kind": "next_work",
            "scope": "work",
            "authority": "READ",
            "fetch_mission": {"planned_tools": planned_tools_for_kind("next_work")},
            "capability_contract": {"allowed": ["attention.get_current"], "unavailable": []},
        },
        tool_results=[
            {
                "name": "attention.get_current",
                "ok": True,
                "data": {"needs_you_count": 2, "evidence_ids": ["need_1", "need_2"]},
            }
        ],
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
    )
    assert any(
        assertion.subject == "attention"
        and assertion.predicate == "needs_you_count"
        and assertion.value == 2
        for assertion in bundle.grounded_assertions
    )


def test_bundle_preserves_conflicting_assertions_without_last_write_wins() -> None:
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
                            "id": "user_works_monday",
                            "subject": "user",
                            "predicate": "works_monday",
                            "value": True,
                            "temporal_scope": "2026-08-17",
                            "epistemic_status": "user_confirmed",
                        },
                        {
                            "id": "holiday_monday",
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

    assert {assertion.id for assertion in bundle.grounded_assertions} == {
        "user_works_monday",
        "holiday_monday",
    }
    assert bundle.conflicts
    assert bundle.conflicts[0].field == "user.works_monday"


def test_bundle_preserves_qualifying_challenge_without_forcing_contradiction() -> None:
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
                            "id": "user_works_monday",
                            "subject": "user",
                            "predicate": "works_monday",
                            "value": True,
                            "temporal_scope": "2026-08-17",
                            "epistemic_status": "user_confirmed",
                        }
                    ],
                    "challenges": [
                        {
                            "claim_id": "user_works_monday",
                            "related_assertion_ids": ["bank_holiday"],
                            "subject": "user",
                            "predicate": "works_monday",
                            "disposition": "qualifies",
                            "summary": (
                                "Monday is a bank holiday, so work status needs "
                                "confirmation rather than inversion."
                            ),
                            "evidence_refs": ["holiday_1"],
                        }
                    ],
                },
            }
        ],
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
    )

    assert any(
        challenge.disposition == ChallengeDisposition.QUALIFIES
        for challenge in bundle.challenges
    )
    assert not bundle.conflicts


def test_hallucination_fossil_does_not_gain_verified_status_from_repetition() -> None:
    inferred = GroundedAssertion(
        id="assistant_fossil",
        subject="person_b",
        predicate="likes_ceramics",
        value=True,
        epistemic_status=EpistemicStatus.MODEL_INFERRED,
        derivation_kind=DerivationKind.DIALOGUE_HISTORY,
        validity_kind=AssertionValidityKind.DERIVED_LIFETIME,
        derived_from=["turn_1", "turn_2"],
    )
    repeated = GroundedAssertion.model_validate(inferred.model_dump())

    assert repeated.epistemic_status == EpistemicStatus.MODEL_INFERRED
    assert repeated.derivation_kind == DerivationKind.DIALOGUE_HISTORY


def test_expired_embedded_assertion_is_preserved_but_not_current() -> None:
    now = datetime(2026, 8, 18, 9, 0, tzinfo=UTC)
    expired = GroundedAssertion(
        id="forecast_old",
        subject="weather",
        predicate="rain_expected",
        value=True,
        epistemic_status=EpistemicStatus.EXTERNALLY_VERIFIED,
        validity_kind=AssertionValidityKind.TTL,
        valid_until=now - timedelta(minutes=5),
    )

    bundle = build_evidence_bundle(
        question="should i bring an umbrella?",
        working_set={
            "authority": "NONE",
            "capability_contract": {"allowed": [], "unavailable": []},
        },
        tool_results=[
            {
                "name": "world.explain",
                "ok": True,
                "data": {"grounded_assertions": [expired.model_dump(mode="json")]},
            }
        ],
    )

    restored = next(
        assertion
        for assertion in bundle.grounded_assertions
        if assertion.id == "forecast_old"
    )
    assert restored.is_usable_now(now=now) is False


def test_subject_id_collected_as_evidence_ref() -> None:
    bundle = build_evidence_bundle(
        question="why is this on my list?",
        working_set={
            "request_kind": "support_explain",
            "authority": "READ",
            "fetch_mission": {"planned_tools": ["world.explain"]},
            "capability_contract": {"allowed": ["world.explain"], "unavailable": []},
        },
        tool_results=[
            {
                "name": "world.explain",
                "ok": True,
                "data": {"subject_id": "item-obligation_token_audit"},
            }
        ],
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
    )
    assert bundle.evidence
    assert "item-obligation_token_audit" in bundle.evidence[0].evidence_ids


def test_partial_coverage_with_evidence_qualifies_not_addresses() -> None:
    bundle = build_evidence_bundle(
        question="what have i missed?",
        working_set={
            "request_kind": "catch_up",
            "scope": "work",
            "authority": "READ",
            "fetch_mission": {"planned_tools": planned_tools_for_kind("catch_up")},
            "capability_contract": {"allowed": ["agenda.get"], "unavailable": []},
        },
        tool_results=[
            {
                "name": "agenda.get",
                "ok": True,
                "data": {
                    "period": "today",
                    "calendar_evidence_ids": ["cal_1"],
                },
            }
        ],
        evidence_domain="PRIVATE_WORLD",
        authority="READ",
    )
    assert any(challenge.disposition == "qualifies" for challenge in bundle.challenges)
