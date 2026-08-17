"""Tests for privacy ablation (R06)."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.evaluation._testing.judge_mock import PerCandidateJudgeMockTransport
from personal_enigma.evaluation.evaluation_truth import load_evaluation_truth
from personal_enigma.evaluation.llm_benchmark import snapshot_to_transformed_context
from personal_enigma.evaluation.privacy_ablation import run_privacy_ablation
from personal_enigma.reasoning import PaygReasoningService, ReasoningMode, RecordingPaygTransport
from personal_enigma.reasoning.privacy_gate import assert_remote_safe

REPO = Path(__file__).resolve().parents[3]
GT = REPO / "scenarios" / "alex-v1" / "ground_truth"
BASELINES = Path(__file__).resolve().parents[1] / "fixtures" / "baselines" / "arm-a"


def test_transformed_context_passes_privacy_gate() -> None:
    from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot

    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-14T10:00.json")
    assert_remote_safe(snapshot_to_transformed_context(snap))


def test_ablation_delta_computed(tmp_path: Path) -> None:
    truth = load_evaluation_truth(GT)
    recorder = RecordingPaygTransport(
        PerCandidateJudgeMockTransport(), scenario="ablation"
    )
    from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
    from personal_enigma.evaluation.llm_benchmark import score_arm_b

    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-14T10:00.json")
    service = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=recorder)
    score_arm_b(
        snap,
        truth,
        service=service,
        context=snapshot_to_transformed_context(snap),
    )
    path = tmp_path / "replay.json"
    recorder.save(path)

    report = run_privacy_ablation(
        truth,
        baseline_dir=BASELINES,
        replay_fixture=path,
        checkpoint_ids=["cp-2026-01-14T10:00"],
    )
    assert report.transformed_passes_privacy_gate
    assert "critical_recall" in report.delta
