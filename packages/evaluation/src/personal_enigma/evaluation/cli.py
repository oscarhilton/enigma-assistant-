"""CLI: ``enigma-eval`` / ``uv run enigma-eval``.

Writes ``reports/<run_id>/`` with summary, metrics, failures, timeline,
privacy, and cost artefacts. Demo Mode only — never reads Private roots.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from personal_enigma.evaluation.observations import (
    CostEvent,
    EvaluationObservations,
    PrivacyProbe,
    SurfacedAlert,
)
from personal_enigma.evaluation.runner import EvaluationRunner


def _load_observations(path: Path | None) -> EvaluationObservations:
    if path is None:
        return EvaluationObservations(evaluated_at=datetime.now(tz=UTC))
    raw = json.loads(path.read_text(encoding="utf-8"))
    return EvaluationObservations.model_validate(raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="enigma-eval",
        description="Run Demo Mode evaluation and write reports/<run_id>/",
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default="alex-v1",
        help="Scenario id under scenarios/ (default: alex-v1)",
    )
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=None,
        help="Path to ground_truth/ directory or YAML file",
    )
    parser.add_argument(
        "--observations",
        type=Path,
        default=None,
        help="JSON file of EvaluationObservations",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("reports"),
        help="Root directory for reports/<run_id>/ (default: reports)",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional fixed run id",
    )
    parser.add_argument(
        "--scenario-version",
        default="0.0.0",
        help="Scenario version recorded in summary.json",
    )
    parser.add_argument(
        "--scenario-days",
        type=float,
        default=1.0,
        help="Scenario duration in days for cost extrapolation",
    )
    parser.add_argument(
        "--spine-metrics",
        type=Path,
        default=None,
        help="JSON metrics from spine-only (A) run for storyline recall under noise",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute metrics without writing reports/",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    observations = _load_observations(args.observations)
    if args.spine_metrics is not None:
        spine = json.loads(args.spine_metrics.read_text(encoding="utf-8"))
        if not isinstance(spine, dict):
            print(
                f"--spine-metrics must be a JSON object, got {type(spine).__name__}",
                file=sys.stderr,
            )
            return 2
        observations = observations.model_copy(update={"spine_metrics": spine})
    runner = EvaluationRunner(
        reports_root=args.reports_dir,
        scenario_days=args.scenario_days,
    )
    report = runner.run(
        args.scenario,
        ground_truth_path=args.ground_truth,
        observations=observations,
        run_id=args.run_id,
        write=not args.dry_run,
        scenario_version=args.scenario_version,
    )
    print(json.dumps(report.summary, indent=2))
    if report.report_dir is not None:
        print(f"report_dir={report.report_dir}", file=sys.stderr)
    return 0 if report.status == "pass" else 1


# Helpers exposed for smoke fixtures / docs
def demo_observations_for_smoke() -> EvaluationObservations:
    """Tiny observation set used by tests and README examples."""
    return EvaluationObservations(
        evaluated_at=datetime(2026, 3, 20, 11, 0, tzinfo=UTC),
        alerts=[
            SurfacedAlert(
                id="alert-1",
                title="Review Atlas proposal",
                obligation_ids=["obligation_atlas_review"],
                surfaced_at=datetime(2026, 3, 20, 10, 0, tzinfo=UTC),
            )
        ],
        privacy_probes=[
            PrivacyProbe(
                id="probe-safe",
                source_type="email",
                payload={
                    "summary": "Review proposal",
                    "entities": ["PERSON_A1B2C3"],
                    "may_transmit_remotely": True,
                    "metadata": {"source_type": "email"},
                },
            )
        ],
        cost_events=[
            CostEvent(
                category="attention_reasoning",
                model="stub",
                input_tokens=100,
                output_tokens=20,
                estimated_usd=0.01,
            )
        ],
        provider="stub",
        model="stub",
        prompt_versions={"attention_assessment": "v0"},
    )


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["build_parser", "demo_observations_for_smoke", "main"]
