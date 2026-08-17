"""Tests for offline transform re-gate (R-L09 Phase 3c)."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.evaluation.transform_regate import run_offline_transform_regate

BASELINES = (
    Path(__file__).resolve().parents[1] / "fixtures" / "baselines" / "arm-a"
)


def test_offline_regate_runs_without_llm() -> None:
    report = run_offline_transform_regate(
        baseline_dir=BASELINES,
        checkpoint_ids=["cp-2026-01-19T10:00", "cp-2026-01-20T11:00"],
    )
    assert len(report.offline_gates) >= 2
    assert report.rationale
    assert isinstance(report.recommend_live_hardest_10, bool)
