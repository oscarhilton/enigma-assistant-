"""Tests for offline transform gate checklist (R-L09)."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
from personal_enigma.evaluation.llm_benchmark import snapshot_to_production_transformed
from personal_enigma.evaluation.transform_diff import diff_checkpoint_transform
from personal_enigma.evaluation.transform_regate import run_offline_transform_regate
from personal_enigma.evaluation.transform_semantic_audit import audit_offline_transform_gate

BASELINES = (
    Path(__file__).resolve().parents[1] / "fixtures" / "baselines" / "arm-a"
)
REGRESSION_CPS = ["cp-2026-01-19T10:00", "cp-2026-01-20T11:00"]


def test_jan19_offline_gate_passes_with_blocker_causality() -> None:
    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-19T10:00.json")
    ctx = snapshot_to_production_transformed(snap)
    gate = audit_offline_transform_gate(snap, ctx)
    assert gate.evidence_ids_present
    assert gate.raw_identity_absent
    assert gate.dependency_represented
    assert gate.blocker_resolution_represented
    assert gate.causal_actionability_transition
    token_blocked = [
        r
        for r in ctx.relations
        if r.subject == "TASK_TOKEN_AUDIT" and r.type == "BLOCKED_BY"
    ]
    assert token_blocked and token_blocked[0].state == "resolved"


def test_jan19_diff_reports_no_lost_semantic_gaps() -> None:
    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-19T10:00.json")
    report = diff_checkpoint_transform(snap)
    assert report.offline_gate is not None
    assert report.offline_gate.passed
    lost = [loss for loss in report.losses if not loss.acceptable]
    assert not any(
        loss.loss_class.value
        in ("dependency_blocker", "resolution_evidence", "causal_relation")
        for loss in lost
    )


def test_offline_regate_does_not_recommend_live_when_gates_fail(monkeypatch) -> None:
    report = run_offline_transform_regate(
        baseline_dir=BASELINES,
        checkpoint_ids=REGRESSION_CPS,
    )
    assert report.offline_gates
    if all(g.passed for g in report.offline_gates):
        assert report.recommend_live_hardest_10
    else:
        assert not report.recommend_live_hardest_10
