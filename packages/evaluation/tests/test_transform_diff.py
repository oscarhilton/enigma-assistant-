"""Tests for transform diff diagnostic (R-L09)."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
from personal_enigma.evaluation.transform_diff import (
    diff_checkpoint_transform,
    run_transform_diff,
)

BASELINES = (
    Path(__file__).resolve().parents[1] / "fixtures" / "baselines" / "arm-a"
)


def test_diff_regression_checkpoint_has_resolved_blocker() -> None:
    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-19T10:00.json")
    report = diff_checkpoint_transform(snap)
    assert report.checkpoint_id == "cp-2026-01-19T10:00"
    assert report.offline_gate is not None
    assert report.offline_gate.passed
    assert (
        report.evaluation_transformed_v1["metadata"]["context_mode"]
        == "evaluation_transformed_v1"
    )
    assert report.evaluation_transformed_v1["metadata"].get("frozen") is True
    assert (
        report.evaluation_transformed_v2["metadata"]["context_mode"]
        == "evaluation_transformed_v2"
    )
    rels = report.evaluation_transformed_v2.get("relations", [])
    token_blocked = [
        r for r in rels if r.get("subject") == "TASK_TOKEN_AUDIT" and r.get("type") == "BLOCKED_BY"
    ]
    assert token_blocked
    assert token_blocked[0]["state"] == "resolved"
    assert "actionable" in (token_blocked[0].get("causal") or "").lower()


def test_run_transform_diff_two_checkpoints() -> None:
    ids = ["cp-2026-01-19T10:00", "cp-2026-01-20T11:00"]
    reports = run_transform_diff(baseline_dir=BASELINES, checkpoint_ids=ids)
    assert len(reports) == 2
    assert all(r.production_transform_gap for r in reports)
