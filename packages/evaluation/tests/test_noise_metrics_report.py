"""Mini-fixture coverage for corpus plan §38–48 noise metrics in enigma-eval."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from personal_enigma.evaluation import EvaluationRunner, load_ground_truth
from personal_enigma.evaluation.cli import main
from personal_enigma.evaluation.observations import (
    CostEvent,
    EvaluationObservations,
    SurfacedAlert,
)

FIXTURES = Path(__file__).parent / "fixtures" / "noise_mini"
TRUTH = FIXTURES / "ground_truth"
OBS = FIXTURES / "observations.json"
SPINE = FIXTURES / "spine_metrics.json"


def test_noise_mini_report_includes_plan_metrics(tmp_path: Path) -> None:
    truth = load_ground_truth(TRUTH)
    observations = EvaluationObservations.model_validate_json(
        OBS.read_text(encoding="utf-8")
    )
    report = EvaluationRunner(
        reports_root=tmp_path / "reports",
        scenario_days=30.0,
    ).run(
        "noise-mini",
        ground_truth=truth,
        observations=observations,
        run_id="noise-mini-001",
    )
    assert report.status == "pass"
    assert report.report_dir is not None
    metrics = json.loads((report.report_dir / "metrics.json").read_text(encoding="utf-8"))

    suppression = metrics["suppression"]
    assert suppression["background_count"] == 4
    assert suppression["noise_count"] == 2
    assert suppression["background_suppression_rate"] == 1.0
    assert suppression["background_false_alerts_per_1000"] == 0.0
    assert suppression["attention_compression_ratio"] == 6.0  # 6 signals : 1 alert

    scale = metrics["scale"]
    assert scale["attention_compression_ratio"] == 6.0
    assert scale["remote_reasoning_rate_per_1k"] == 0.0
    assert "cost_per_1k_messages" in scale

    cost = metrics["cost"]
    assert cost["cost_per_simulated_month"] == cost["monthly_usd"]
    # 0.03 USD over 30 scenario days → daily 0.001 → monthly 0.03
    assert abs(cost["cost_per_simulated_month"] - 0.03) < 1e-9

    ab = metrics["storyline_recall_under_noise"]
    assert ab["spine_critical_recall"] == 1.0
    assert ab["with_background_critical_recall"] == 1.0
    assert ab["passed"]

    md = (report.report_dir / "SUMMARY.md").read_text(encoding="utf-8")
    assert "Background suppression rate" in md
    assert "Storyline recall under noise" in md
    assert "Remote reasoning rate" in md


def test_noise_mini_false_alert_fails_ceiling(tmp_path: Path) -> None:
    truth = load_ground_truth(TRUTH)
    observations = EvaluationObservations(
        evaluated_at=datetime(2026, 3, 20, 11, 0, tzinfo=UTC),
        alerts=[
            SurfacedAlert(
                id="alert-critical",
                obligation_ids=["obligation_atlas_review"],
                evidence_ids=["canonical-1"],
            ),
            SurfacedAlert(id="false-bg", evidence_ids=["bg-1"]),
            SurfacedAlert(id="false-noise", evidence_ids=["noise-1"]),
        ],
        cost_events=[CostEvent(estimated_usd=0.01)],
        message_count=6,
        remote_calls=1,
        spine_metrics={"attention": {"critical_recall": 1.0}},
    )
    report = EvaluationRunner(reports_root=tmp_path / "reports").run(
        "noise-mini-fail",
        ground_truth=truth,
        observations=observations,
        run_id="noise-mini-fail-001",
        write=False,
    )
    assert report.status == "suppression_fail"
    # 2 false / 6 messages * 1000 ≈ 333.3
    assert report.metrics["suppression"]["background_false_alerts_per_1000"] > 1.0
    assert report.metrics["scale"]["remote_reasoning_rate_per_1k"] > 0


def test_cli_spine_metrics_flag(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    reports = tmp_path / "reports"
    monkeypatch.chdir(tmp_path)
    code = main(
        [
            "noise-mini",
            "--ground-truth",
            str(TRUTH),
            "--observations",
            str(OBS),
            "--spine-metrics",
            str(SPINE),
            "--reports-dir",
            str(reports),
            "--run-id",
            "cli-noise-001",
            "--scenario-days",
            "30",
        ]
    )
    assert code == 0
    metrics = json.loads(
        (reports / "cli-noise-001" / "metrics.json").read_text(encoding="utf-8")
    )
    assert "storyline_recall_under_noise" in metrics
    assert metrics["suppression"]["background_suppression_rate"] == 1.0
