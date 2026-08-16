"""Smoke + schema tests for the evaluation runner (D7)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from personal_enigma.evaluation import EvaluationRunner, load_ground_truth
from personal_enigma.evaluation.cli import demo_observations_for_smoke, main
from personal_enigma.evaluation.metrics import attention, cost, memory, privacy, retrieval
from personal_enigma.evaluation.observations import (
    CostEvent,
    EvaluationObservations,
    PrivacyProbe,
    SurfacedAlert,
)
from personal_enigma.evaluation.regression import compare_to_baseline
from personal_enigma.evaluation.report import REPORT_FILES

FIXTURES = Path(__file__).parent / "fixtures"
SMOKE_TRUTH = FIXTURES / "ground_truth" / "missed_critical"


def test_metric_primitives() -> None:
    assert attention.critical_recall(predicted=9, expected=10) == 0.9
    assert attention.precision(useful=8, total=10) == 0.8
    assert attention.duplicate_rate(duplicates=1, total=20) == 0.05
    assert attention.stale_alert_rate(stale=1, total=50) == 0.02
    assert privacy.direct_identifier_leaks(count=0) == 0
    assert memory.checkpoint_hit_rate(hits=1, total=2) == 0.5
    assert retrieval.recall_at_k(hits=3, k=5) == 0.6
    assert cost.total_usd(amount=1.25) == 1.25


def test_smoke_run_writes_report_layout(tmp_path: Path) -> None:
    truth = load_ground_truth(SMOKE_TRUTH)
    observations = demo_observations_for_smoke()
    runner = EvaluationRunner(reports_root=tmp_path / "reports")
    report = runner.run(
        "missed-critical-smoke",
        ground_truth=truth,
        observations=observations,
        run_id="smoke-run-001",
    )
    assert report.status == "pass"
    assert report.report_dir is not None
    assert report.report_dir.is_dir()
    for name in REPORT_FILES:
        assert (report.report_dir / name).is_file(), name

    metrics = json.loads((report.report_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["attention"]["critical_recall"] == 1.0
    assert metrics["privacy"]["direct_identifier_leaks"] == 0
    assert "total_usd" in metrics["cost"]
    assert metrics["memory"]["checkpoint_hit_rate"] == 1.0


def test_report_json_markdown_schema_snapshot(tmp_path: Path) -> None:
    truth = load_ground_truth(SMOKE_TRUTH)
    observations = EvaluationObservations(
        evaluated_at=datetime(2026, 3, 20, 11, 0, tzinfo=UTC),
        alerts=[],  # miss critical → attention_miss
        privacy_probes=[],
        cost_events=[CostEvent(estimated_usd=0.02)],
    )
    report = EvaluationRunner(reports_root=tmp_path / "reports").run(
        "schema-snap",
        ground_truth=truth,
        observations=observations,
        run_id="schema-snap-001",
    )
    assert report.status == "attention_miss"
    assert report.report_dir is not None

    summary = json.loads((report.report_dir / "summary.json").read_text(encoding="utf-8"))
    metrics = json.loads((report.report_dir / "metrics.json").read_text(encoding="utf-8"))
    failures = json.loads((report.report_dir / "failures.json").read_text(encoding="utf-8"))
    md = (report.report_dir / "SUMMARY.md").read_text(encoding="utf-8")

    assert set(summary) >= {
        "run_id",
        "scenario",
        "scenario_version",
        "status",
        "evaluated_at",
        "environment",
        "privacy_policy_version",
    }
    assert set(metrics) == {
        "attention",
        "privacy",
        "memory",
        "retrieval",
        "cost",
        "scale",
    }
    assert "attention_compression_ratio" in metrics["scale"]
    for key in (
        "critical_recall",
        "precision",
        "duplicate_rate",
        "stale_alert_rate",
    ):
        assert key in metrics["attention"]
    assert "missed_obligations" in failures
    assert failures["missed_obligations"][0]["obligation_id"] == "obligation_atlas_review"
    assert md.startswith("# Evaluation report `schema-snap-001`")
    assert "Critical recall" in md


def test_privacy_probe_detects_email_leak(tmp_path: Path) -> None:
    from uuid import uuid4

    observations = EvaluationObservations(
        evaluated_at=datetime(2026, 3, 20, 11, 0, tzinfo=UTC),
        alerts=[
            SurfacedAlert(
                id="obligation_atlas_review",
                obligation_ids=["obligation_atlas_review"],
            )
        ],
        privacy_probes=[
            PrivacyProbe(
                id="leaky",
                source_type="email",
                payload={
                    "summary": "Contact maya@example.com about Atlas",
                    "entities": ["PERSON_A1B2C3"],
                    "may_transmit_remotely": True,
                    "metadata": {"source_type": "email"},
                },
                people=[
                    {
                        "id": str(uuid4()),
                        "display_name": "Maya Chen",
                        "email_addresses": ["maya@example.com"],
                    }
                ],
            )
        ],
    )
    report = EvaluationRunner(reports_root=tmp_path / "reports").run(
        "privacy-smoke",
        ground_truth=load_ground_truth(SMOKE_TRUTH),
        observations=observations,
        run_id="privacy-smoke-001",
    )
    assert report.status == "privacy_fail"
    assert report.metrics["privacy"]["direct_identifier_leaks"] >= 1


def test_cli_writes_reports(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    obs_path = tmp_path / "obs.json"
    obs_path.write_text(
        demo_observations_for_smoke().model_dump_json(),
        encoding="utf-8",
    )
    reports = tmp_path / "reports"
    monkeypatch.chdir(tmp_path)
    # ground truth lives in package fixtures — pass absolute path
    code = main(
        [
            "smoke",
            "--ground-truth",
            str(SMOKE_TRUTH),
            "--observations",
            str(obs_path),
            "--reports-dir",
            str(reports),
            "--run-id",
            "cli-run-001",
        ]
    )
    assert code == 0
    assert (reports / "cli-run-001" / "summary.json").is_file()


def test_regression_baseline_flags_pii() -> None:
    result = compare_to_baseline(
        {
            "attention": {"critical_recall": 0.99, "duplicate_rate": 0.01},
            "privacy": {"direct_identifier_leaks": 1},
            "cost": {"total_usd": 0.01},
        },
        {
            "attention": {"critical_recall": 0.99, "duplicate_rate": 0.01},
            "privacy": {"direct_identifier_leaks": 0},
            "cost": {"total_usd": 0.01},
        },
    )
    assert result.passed is False
    assert any("direct_identifier" in v for v in result.violations)


def test_regression_flags_false_alerts_per_1k() -> None:
    result = compare_to_baseline(
        {
            "attention": {"critical_recall": 1.0, "duplicate_rate": 0.0},
            "privacy": {"direct_identifier_leaks": 0},
            "cost": {"total_usd": 0.01},
            "scale": {"false_alerts_per_1k": 5.0},
        },
        {
            "attention": {"critical_recall": 1.0, "duplicate_rate": 0.0},
            "privacy": {"direct_identifier_leaks": 0},
            "cost": {"total_usd": 0.01},
        },
    )
    assert result.passed is False
    assert any("false_alerts" in v for v in result.violations)


def test_duplicates_and_stale_counted(tmp_path: Path) -> None:
    truth = load_ground_truth(SMOKE_TRUTH)
    observations = EvaluationObservations(
        evaluated_at=datetime(2026, 3, 20, 11, 0, tzinfo=UTC),
        alerts=[
            SurfacedAlert(
                id="a1",
                obligation_ids=["obligation_atlas_review"],
            ),
            SurfacedAlert(
                id="a2",
                obligation_ids=["obligation_atlas_review"],
                duplicate_of="a1",
            ),
            SurfacedAlert(
                id="a3",
                obligation_ids=["obligation_atlas_review"],
                resolved_underlying=True,
            ),
        ],
    )
    report = EvaluationRunner(reports_root=tmp_path / "reports").run(
        "dup-stale",
        ground_truth=truth,
        observations=observations,
        run_id="dup-stale-001",
        write=False,
    )
    att = report.metrics["attention"]
    assert att["duplicate_alerts"] == 1
    assert att["stale_alerts"] == 1
    assert att["duplicate_rate"] == 1 / 3
    assert att["stale_alert_rate"] == 1 / 3
