"""Tests for live Reasoning Value Gate orchestration (R-L04–L08)."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.evaluation.evaluation_truth import load_evaluation_truth
from personal_enigma.evaluation.live_gate import (
    SMOKE_CASES,
    run_live_gate,
    run_smoke_gate,
)
from personal_enigma.evaluation.reasoning_value_gate import decide_live_architecture

REPO = Path(__file__).resolve().parents[3]
GT = REPO / "scenarios" / "alex-v1" / "ground_truth"
BASELINES = Path(__file__).resolve().parents[1] / "fixtures" / "baselines" / "arm-a"


def test_smoke_gate_mock_passes_unanimous() -> None:
    truth = load_evaluation_truth(GT)
    report = run_smoke_gate(truth, baseline_dir=BASELINES, live=False)
    assert report.passed
    assert len(report.outcomes) == len(SMOKE_CASES) * 3
    assert all(o.passed for o in report.outcomes)


def test_decide_live_architecture_clear_win() -> None:
    decision, _ = decide_live_architecture(
        {"critical_recall": 0.5, "must_suppress_accuracy": 1.0},
        {"critical_recall": 0.9, "must_suppress_accuracy": 1.0},
        critical_regressions=0,
        schema_failure_rate=0.0,
        privacy_failure_rate=0.0,
    )
    assert decision == "clear_win"


def test_decide_live_architecture_no_win() -> None:
    decision, _ = decide_live_architecture(
        {"critical_recall": 0.9, "must_suppress_accuracy": 1.0},
        {"critical_recall": 0.5, "must_suppress_accuracy": 0.8},
        critical_regressions=2,
        schema_failure_rate=0.1,
        privacy_failure_rate=0.0,
    )
    assert decision == "no_win"


def test_live_gate_mock_main_phase(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    truth = load_evaluation_truth(GT)
    result = run_live_gate(
        ground_truth_path=GT,
        baseline_dir=BASELINES,
        phase="main",
        live=False,
        write_report=False,
    )
    assert result.main is not None
    assert result.main.checkpoint_ids
    assert result.main.arm_a_aggregate
