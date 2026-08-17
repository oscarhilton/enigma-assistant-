"""Offline composite decomposition (R-L10 Phase 1) — no live model spend."""

from __future__ import annotations

from pathlib import Path

import pytest

from personal_enigma.attention.interruption_policy import (
    SURFACE_SCORE_THRESHOLD,
    WEIGHT_ACTIONABILITY_NOW,
    WEIGHT_TIME_SENSITIVITY,
    composite_surface_score,
    decide_interruption,
)
from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
from personal_enigma.evaluation.composite_decomposition import (
    DEFAULT_STEP7_JSON,
    JAN19_20_CHECKPOINTS,
    TOKEN_CANDIDATE_ID,
    TokenAuditLayer,
    classify_token_audit,
    decompose_rep,
    decompose_step7_json,
    deterministic_boosts,
)
from personal_enigma.evaluation.evaluation_truth import load_evaluation_truth
from personal_enigma.evaluation.llm_benchmark import (
    build_candidate_policy_facts,
    semantic_output_to_features,
)
from personal_enigma.reasoning.structured_output import SemanticJudgeV1Output

REPO = Path(__file__).resolve().parents[3]
GT = REPO / "scenarios" / "alex-v1" / "ground_truth"
BASELINES = Path(__file__).resolve().parents[1] / "fixtures" / "baselines" / "arm-a"
STEP7 = REPO / DEFAULT_STEP7_JSON


def test_classify_token_audit_qualification_failure() -> None:
    layer = classify_token_audit(
        composite=0.67,
        decision="context",
        rank=None,
        contract_pass=False,
    )
    assert layer is TokenAuditLayer.QUALIFICATION_FAILURE


def test_classify_token_audit_other_gate() -> None:
    layer = classify_token_audit(
        composite=0.80,
        decision="suppress",
        rank=None,
        contract_pass=False,
    )
    assert layer is TokenAuditLayer.OTHER_GATE


def test_classify_token_audit_outside_top3() -> None:
    layer = classify_token_audit(
        composite=0.80,
        decision="surface",
        rank=4,
        contract_pass=False,
    )
    assert layer is TokenAuditLayer.OUTSIDE_TOP3


def test_classify_token_audit_eval_bug() -> None:
    layer = classify_token_audit(
        composite=0.80,
        decision="surface",
        rank=2,
        contract_pass=False,
    )
    assert layer is TokenAuditLayer.EVAL_BUG


def test_classify_token_audit_surfaced_in_top3() -> None:
    layer = classify_token_audit(
        composite=0.7475,
        decision="surface",
        rank=2,
        contract_pass=True,
    )
    assert layer is TokenAuditLayer.SURFACED_IN_TOP3


def test_jan20_token_near_term_boost_brunch_calendar_boost() -> None:
    truth = load_evaluation_truth(GT)
    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-20T11:00.json")
    token = next(c for c in snap.candidate_set if c.id == TOKEN_CANDIDATE_ID)
    brunch = next(c for c in snap.candidate_set if c.id == "item-obligation_brunch_book")
    token_facts = build_candidate_policy_facts(snap, token, truth)
    brunch_facts = build_candidate_policy_facts(snap, brunch, truth)
    semantic = semantic_output_to_features(
        SemanticJudgeV1Output(
            obligation_strength=0.8,
            user_responsibility=0.7,
            importance=0.6,
            time_sensitivity=0.3,
            actionability_now=0.9,
            confidence=0.95,
        )
    )
    token_boosts = deterministic_boosts(semantic, token_facts)
    brunch_boosts = deterministic_boosts(semantic, brunch_facts)
    assert token_facts.hours_until_due == 30.0
    assert token_boosts.near_term_boost == pytest.approx(0.10 * (1.0 - 30.0 / 36.0))
    assert token_boosts.calendar_boost == 0.0
    assert brunch_facts.hours_until_due == 49.0
    assert brunch_boosts.near_term_boost == 0.0
    assert brunch_boosts.calendar_boost == 0.05
    assert WEIGHT_TIME_SENSITIVITY > WEIGHT_ACTIONABILITY_NOW


def test_decompose_rep_matches_production_policy() -> None:
    truth = load_evaluation_truth(GT)
    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-19T10:00.json")
    semantic = {
        "schema_version": "semantic-judge-v1",
        "obligation_strength": 0.9,
        "user_responsibility": 0.8,
        "importance": 0.85,
        "time_sensitivity": 0.4,
        "actionability_now": 0.9,
        "confidence": 0.9,
        "reason_codes": ["USER_OWNS_ACTION"],
    }
    rows = decompose_rep(
        snapshot=snap,
        truth=truth,
        rep_payload={
            "rep": 2,
            "candidate_judgements": [
                {"candidate_id": TOKEN_CANDIDATE_ID, "semantic_output": semantic}
            ],
            "policy_judgement": [
                {
                    "id": TOKEN_CANDIDATE_ID,
                    "score": 0.7474999999999999,
                    "obligation_ids": ["obligation_token_audit"],
                    "title": "Draft colour + spacing token inventory",
                }
            ],
            "metrics": {
                "checkpoint_scores": [
                    {
                        "scenario": "token-inventory-blocker",
                        "attention_pass": True,
                        "attention_reason_codes": [],
                    }
                ]
            },
        },
    )
    assert len(rows) == 1
    row = rows[0]
    feats = semantic_output_to_features(SemanticJudgeV1Output.model_validate(semantic))
    facts = build_candidate_policy_facts(
        snap,
        next(c for c in snap.candidate_set if c.id == TOKEN_CANDIDATE_ID),
        truth,
    )
    assert row.composite == pytest.approx(composite_surface_score(feats, facts))
    assert decide_interruption(feats, facts).decision == "surface"
    assert row.eligible is True
    assert row.composite >= SURFACE_SCORE_THRESHOLD
    assert row.rank == 1
    assert row.stored_matches_recomputed is True


@pytest.mark.skipif(not STEP7.is_file(), reason="frozen Step 7 JSON not present")
def test_step7_token_audit_attention_eligibility_and_critical_recall() -> None:
    report = decompose_step7_json(
        STEP7,
        checkpoint_ids=list(JAN19_20_CHECKPOINTS),
        baseline_dir=BASELINES,
        ground_truth=GT,
    )
    by_key = {(t.checkpoint_id, t.rep): t for t in report.token_audit}
    assert by_key[("cp-2026-01-19T10:00", 0)].layer is TokenAuditLayer.QUALIFICATION_FAILURE
    assert by_key[("cp-2026-01-19T10:00", 1)].layer is TokenAuditLayer.QUALIFICATION_FAILURE
    assert by_key[("cp-2026-01-19T10:00", 2)].layer is TokenAuditLayer.SURFACED_IN_TOP3
    assert by_key[("cp-2026-01-20T11:00", 0)].layer is TokenAuditLayer.QUALIFICATION_FAILURE
    assert by_key[("cp-2026-01-20T11:00", 1)].layer is TokenAuditLayer.QUALIFICATION_FAILURE
    assert by_key[("cp-2026-01-20T11:00", 2)].layer is TokenAuditLayer.QUALIFICATION_FAILURE
    surfaced = [r for r in report.rows if r.stored_policy_score is not None]
    assert surfaced
    assert all(r.stored_matches_recomputed for r in surfaced)
    three = report.three_layer
    assert three["attention_eligibility_recall"] < 1.0
    assert three["critical_recall_at_k"]["1"] <= three["critical_recall_at_k"]["3"]
    assert report.outcome.startswith("C")
