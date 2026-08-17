"""Tests for failure attribution (R05)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from personal_enigma.evaluation.evaluation_truth import load_evaluation_truth
from personal_enigma.evaluation.failure_attribution import (
    FailureCause,
    attribute_checkpoint_disagreements,
    enrich_failures_json,
)
from personal_enigma.evaluation.llm_benchmark import CheckpointArmResult
from personal_enigma.evaluation.metrics.support_fitness import SupportFitnessMetrics
from personal_enigma.evaluation.observations import (
    CheckpointSnapshot,
    MemoryObservation,
)

REPO = Path(__file__).resolve().parents[3]
GT = REPO / "scenarios" / "alex-v1" / "ground_truth"


def _metrics(*, att: float, na: float = 1.0, na_scored: int = 0) -> SupportFitnessMetrics:
    return SupportFitnessMetrics(
        actionability=1.0,
        task_size_fit=1.0,
        friction_reduction=1.0,
        timing_fit=1.0,
        suppression_accuracy=1.0,
        top3_critical_recall=att,
        attention_accuracy=att,
        next_action_accuracy=na,
        contracts_scored=1,
        next_action_checkpoints_scored=na_scored,
        passed=att >= 1.0 and na >= 1.0,
    )


def test_brunch_miss_retrieval_attribution() -> None:
    truth = load_evaluation_truth(GT)
    at = datetime(2026, 1, 21, 13, 30, tzinfo=UTC)
    snap = CheckpointSnapshot(
        checkpoint_id="cp-brunch",
        at=at,
        alerts=[],
        memory_state=MemoryObservation(at=at, open_obligation_ids=[]),
        retrieval=[],
    )
    arm_a = CheckpointArmResult("cp-brunch", "A", _metrics(att=0.0))
    arm_b = CheckpointArmResult("cp-brunch", "B", _metrics(att=1.0))
    cases = attribute_checkpoint_disagreements(
        snap, truth, arm_a=arm_a, arm_b=arm_b
    )
    assert cases
    allowed = {
        FailureCause.RETRIEVAL,
        FailureCause.INGESTION,
        FailureCause.INTERPRETATION,
    }
    assert cases[0].cause in allowed


def test_enrich_failures_json() -> None:
    from personal_enigma.evaluation.failure_attribution import AttributionCase

    case = AttributionCase(
        checkpoint_id="x",
        dimension="attention",
        cause=FailureCause.INTERPRETATION,
        narrative="test",
        arm_a_pass=False,
        arm_b_pass=True,
    )
    out = enrich_failures_json({"missed": []}, [case])
    assert out["attributions"]
    assert out["attribution_summary"]["INTERPRETATION"] == 1
