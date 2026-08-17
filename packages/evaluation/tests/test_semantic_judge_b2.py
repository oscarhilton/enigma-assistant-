"""Integration tests for Arm B2 semantic judge + interruption policy."""

from __future__ import annotations

import json
from pathlib import Path

from personal_enigma.attention.interruption_policy import SemanticFeatures, decide_interruption
from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
from personal_enigma.evaluation.evaluation_truth import load_evaluation_truth
from personal_enigma.evaluation.live_benchmark import SmokeOracleTransport
from personal_enigma.evaluation.llm_benchmark import (
    CandidateJudgement,
    build_candidate_policy_facts,
    rank_semantic_judgements,
    score_arm_b,
    snapshot_to_transformed_context,
)
from personal_enigma.reasoning import PaygReasoningService, ReasoningMode
from personal_enigma.reasoning.structured_output import (
    SemanticJudgeV1Output,
    parse_semantic_judge_v1_output,
)

REPO = Path(__file__).resolve().parents[3]
GT = REPO / "scenarios" / "alex-v1" / "ground_truth"
BASELINES = Path(__file__).resolve().parents[1] / "fixtures" / "baselines" / "arm-a"
SMOKE_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "smoke" / "cp-prizevault-smoke.json"
)


def test_parse_semantic_judge_v1_output() -> None:
    payload = {
        "schema_version": "semantic-judge-v1",
        "obligation_strength": 0.96,
        "user_responsibility": 0.98,
        "importance": 0.82,
        "time_sensitivity": 0.88,
        "actionability_now": 0.91,
        "confidence": 0.95,
        "reason_codes": ["EXPLICIT_REQUEST"],
        "next_action": {"title": "Book the brunch", "estimated_minutes": 10},
    }
    out = parse_semantic_judge_v1_output(json.dumps(payload))
    assert out.schema_version == "semantic-judge-v1"
    assert out.next_action is not None


def test_semantic_oracle_smoke_brunch_surfaces() -> None:
    truth = load_evaluation_truth(GT)
    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-21T13:30.json")
    transport = SmokeOracleTransport(snap.checkpoint_id, judge_arm="b2")
    service = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=transport)
    result = score_arm_b(
        snap,
        truth,
        service=service,
        context=snapshot_to_transformed_context(snap),
        judge_arm="b2",
    )
    assert result.policy_judgement
    assert any(
        "obligation_brunch_book" in a.obligation_ids for a in result.policy_judgement
    )


def test_semantic_oracle_smoke_prizevault_suppresses_noise() -> None:
    truth = load_evaluation_truth(GT)
    snap = load_checkpoint_snapshot(SMOKE_FIXTURE)
    transport = SmokeOracleTransport(snap.checkpoint_id, judge_arm="b2")
    service = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=transport)
    result = score_arm_b(
        snap,
        truth,
        service=service,
        context=snapshot_to_transformed_context(snap),
        judge_arm="b2",
    )
    surfaced_ids = {a.id for a in result.policy_judgement}
    assert "item-noise-prizvault" not in surfaced_ids


def test_semantic_oracle_smoke_quiet_empty_alerts() -> None:
    truth = load_evaluation_truth(GT)
    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-11T11:00.json")
    transport = SmokeOracleTransport(snap.checkpoint_id, judge_arm="b2")
    service = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=transport)
    result = score_arm_b(
        snap,
        truth,
        service=service,
        context=snapshot_to_transformed_context(snap),
        judge_arm="b2",
    )
    assert result.policy_judgement == []


def test_rank_semantic_judgements_integration() -> None:
    truth = load_evaluation_truth(GT)
    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-21T13:30.json")
    candidate = next(c for c in snap.candidate_set if c.id == "item-obligation_brunch_book")
    semantic = SemanticJudgeV1Output(
        obligation_strength=0.96,
        user_responsibility=0.98,
        importance=0.82,
        time_sensitivity=0.88,
        actionability_now=0.91,
        confidence=0.95,
        reason_codes=["EXPLICIT_REQUEST"],
        next_action={"title": "Book the brunch", "estimated_minutes": 10},
    )
    judgements = [
        CandidateJudgement(candidate_id=candidate.id, semantic_output=semantic),
    ]
    ranked = rank_semantic_judgements(snap, judgements, truth)
    assert len(ranked) == 1
    facts = build_candidate_policy_facts(snap, candidate, truth)
    policy = decide_interruption(
        SemanticFeatures(
            obligation_strength=semantic.obligation_strength,
            user_responsibility=semantic.user_responsibility,
            importance=semantic.importance,
            time_sensitivity=semantic.time_sensitivity,
            actionability_now=semantic.actionability_now,
            confidence=semantic.confidence,
        ),
        facts,
    )
    assert policy.decision == "surface"
