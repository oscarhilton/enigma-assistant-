"""Unit tests for deterministic interruption policy (Arm B2)."""

from __future__ import annotations

from datetime import UTC, datetime

from personal_enigma.attention.interruption_policy import (
    CandidatePolicyFacts,
    InterruptionMode,
    SemanticFeatures,
    decide_interruption,
)


def _brunch_semantic() -> SemanticFeatures:
    return SemanticFeatures(
        obligation_strength=0.96,
        user_responsibility=0.98,
        importance=0.82,
        time_sensitivity=0.88,
        actionability_now=0.91,
        confidence=0.95,
        reason_codes=("EXPLICIT_REQUEST", "USER_OWNS_ACTION", "NEAR_TERM_COMMITMENT"),
    )


def _prizevault_semantic() -> SemanticFeatures:
    return SemanticFeatures(
        obligation_strength=0.05,
        user_responsibility=0.05,
        importance=0.05,
        time_sensitivity=0.05,
        actionability_now=0.05,
        confidence=0.95,
        reason_codes=("LOW_VALUE_NOISE",),
    )


def _quiet_weekend_semantic() -> SemanticFeatures:
    return SemanticFeatures(
        obligation_strength=0.50,
        user_responsibility=0.45,
        importance=0.40,
        time_sensitivity=0.20,
        actionability_now=0.15,
        confidence=0.92,
        reason_codes=("LOW_URGENCY", "CONTEXT_ONLY"),
    )


def test_brunch_weekday_surfaces() -> None:
    facts = CandidatePolicyFacts(
        candidate_id="item-obligation_brunch_book",
        now=datetime(2026, 1, 21, 13, 30, tzinfo=UTC),
        candidate_kind="explicit_reminder",
        obligation_ids=("obligation_brunch_book",),
        evidence_ids=("rem-brunch-book", "cal-brunch-parents"),
        has_open_obligation=True,
        due_at=datetime(2026, 1, 22, 12, 0, tzinfo=UTC),
        has_existing_reminder=True,
        calendar_proximity_hours=0.5,
        interruption_mode=InterruptionMode.NORMAL,
    )
    result = decide_interruption(_brunch_semantic(), facts)
    assert result.decision == "surface"
    assert result.reason == "composite_surface"


def test_prizevault_noise_suppresses() -> None:
    facts = CandidatePolicyFacts(
        candidate_id="item-noise-prizvault",
        now=datetime(2026, 1, 16, 9, 0, tzinfo=UTC),
        candidate_kind="inferred_obligation",
        obligation_ids=(),
        evidence_ids=("mail-noise-prizvault",),
        has_open_obligation=False,
        interruption_mode=InterruptionMode.NORMAL,
        is_noise_evidence=True,
    )
    result = decide_interruption(_prizevault_semantic(), facts)
    assert result.decision == "suppress"
    assert result.reason in {"noise_no_obligation", "noise_evidence", "below_threshold"}


def test_quiet_weekend_suppresses_moderate_semantics() -> None:
    facts = CandidatePolicyFacts(
        candidate_id="item-obligation_brunch_book",
        now=datetime(2026, 1, 11, 11, 0, tzinfo=UTC),
        candidate_kind="explicit_reminder",
        obligation_ids=("obligation_brunch_book",),
        evidence_ids=("rem-brunch-book",),
        has_open_obligation=True,
        due_at=datetime(2026, 1, 22, 12, 0, tzinfo=UTC),
        has_existing_reminder=True,
        interruption_mode=InterruptionMode.RESTFUL_WEEKEND,
    )
    result = decide_interruption(_quiet_weekend_semantic(), facts)
    assert result.decision == "suppress"
    assert result.reason == "restful_weekend"
