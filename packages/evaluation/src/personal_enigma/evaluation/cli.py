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

from personal_enigma.evaluation.live_gate import run_live_gate
from personal_enigma.evaluation.observations import (
    CostEvent,
    EvaluationObservations,
    PrivacyProbe,
    SurfacedAlert,
)
from personal_enigma.evaluation.reasoning_value_gate import run_reasoning_value_gate
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
    parser.add_argument(
        "--life-script",
        default=None,
        help=(
            "Run a Life Script (name or path to .script.yaml). "
            "Deterministic by default; pass --live for Fireworks."
        ),
    )
    parser.add_argument(
        "--reasoning-gate",
        action="store_true",
        help="Run Reasoning Value Gate harness (R07) instead of scenario eval",
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=Path("packages/evaluation/fixtures/baselines/arm-a"),
        help="Arm A baseline directory for reasoning gate",
    )
    parser.add_argument(
        "--replay-fixture",
        type=Path,
        default=None,
        help="Replay JSON for Arm B (required with --reasoning-gate unless dry-run)",
    )
    parser.add_argument(
        "--attention-only",
        action="store_true",
        help="Score Arm B attention only (skip next_action fitness)",
    )
    parser.add_argument(
        "--reasoning-gate-live",
        action="store_true",
        help="Run live Fireworks Reasoning Value Gate (R-L04–L08)",
    )
    parser.add_argument(
        "--smoke-only",
        action="store_true",
        help="Run smoke gate only ($0.05 cap, 3 cases × 3 reps)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live Fireworks calls (requires FIREWORKS_API_KEY)",
    )
    parser.add_argument(
        "--phase",
        choices=[
            "smoke",
            "main",
            "disagreements",
            "ablation",
            "report",
            "hardest-10-v2",
            "all",
        ],
        default="all",
        help="Live gate phase to run (default: all)",
    )
    parser.add_argument(
        "--arm",
        choices=["b1", "b2"],
        default="b2",
        help="Arm B judge path: b1=direct judge-v1, b2=semantic judge + policy (default)",
    )
    parser.add_argument(
        "--transform-diff",
        action="store_true",
        help="Run R-L09 transform diff (offline, no LLM)",
    )
    parser.add_argument(
        "--checkpoints",
        default="cp-2026-01-19T10:00,cp-2026-01-20T11:00",
        help="Comma-separated checkpoint ids for --transform-diff / --composite-decomposition",
    )
    parser.add_argument(
        "--transform-diff-out",
        type=Path,
        default=Path("reports/reasoning-gate-live/transform-diff.json"),
        help="Output path for transform diff report",
    )
    parser.add_argument(
        "--composite-decomposition",
        action="store_true",
        help="R-L10 offline composite replay from frozen Step 7 JSON (no LLM)",
    )
    parser.add_argument(
        "--step7-json",
        type=Path,
        default=Path("reports/reasoning-gate-live/hardest-10-evaluation_transformed_v2.json"),
        help="Frozen Step 7 live report for --composite-decomposition",
    )
    parser.add_argument(
        "--composite-decomposition-out",
        type=Path,
        default=Path("reports/reasoning-gate-live/rl10-jan19-20-decomposition.json"),
        help="Output path for composite decomposition JSON",
    )
    parser.add_argument(
        "--security-overlay",
        action="store_true",
        help=(
            "Opt in to Alex security overlay canaries (also ENIGMA_SECURITY_PROFILE=1). "
            "Default runs exclude canaries from behavioural truth."
        ),
    )
    return parser


def _run_composite_decomposition(args: argparse.Namespace) -> int:
    from personal_enigma.evaluation.composite_decomposition import (
        decompose_step7_json,
        render_markdown_table,
        write_decomposition_report,
    )

    cp_ids = [c.strip() for c in args.checkpoints.split(",") if c.strip()]
    gt = args.ground_truth or Path("scenarios") / "alex-v1" / "ground_truth"
    report = decompose_step7_json(
        args.step7_json,
        checkpoint_ids=cp_ids,
        baseline_dir=args.baseline_dir,
        ground_truth=gt,
    )
    out = write_decomposition_report(report, args.composite_decomposition_out)
    print(render_markdown_table(report.rows))
    print(json.dumps({"output": str(out), "outcome": report.outcome}, indent=2))
    return 0


def _run_transform_diff(args: argparse.Namespace) -> int:
    from personal_enigma.evaluation.transform_diff import (
        run_transform_diff,
        write_transform_diff_report,
    )

    cp_ids = [c.strip() for c in args.checkpoints.split(",") if c.strip()]
    reports = run_transform_diff(baseline_dir=args.baseline_dir, checkpoint_ids=cp_ids)
    out = write_transform_diff_report(reports, output_path=args.transform_diff_out)
    print(json.dumps({"output": str(out), "checkpoints": cp_ids}, indent=2))
    return 0


def _run_live_gate(args: argparse.Namespace) -> int:
    gt = args.ground_truth or Path("scenarios") / "alex-v1" / "ground_truth"
    phase = "smoke" if args.smoke_only else args.phase
    result = run_live_gate(
        ground_truth_path=gt,
        baseline_dir=args.baseline_dir,
        phase=phase,
        smoke_only=args.smoke_only,
        live=args.live,
        write_report=not args.dry_run,
        judge_arm=args.arm,
    )
    payload: dict[str, object] = {
        "blocked": result.blocked,
        "block_reason": result.block_reason,
    }
    if result.smoke is not None:
        payload["smoke"] = result.smoke.as_dict()
    if result.main is not None:
        payload["main"] = result.main.as_dict()
    if result.hardest_10_v2 is not None:
        payload["hardest_10_v2"] = result.hardest_10_v2.as_dict()
    if result.evidence is not None:
        payload["evidence"] = result.evidence.as_dict()
    print(json.dumps(payload, indent=2))
    if result.blocked or (result.smoke is not None and not result.smoke.passed):
        return 1
    return 0


def _run_reasoning_gate(args: argparse.Namespace) -> int:
    gt = args.ground_truth or Path("scenarios") / "alex-v1" / "ground_truth"
    replay = args.replay_fixture
    if replay is None and not args.dry_run:
        print("--replay-fixture required for reasoning gate", file=sys.stderr)
        return 2
    evidence = run_reasoning_value_gate(
        ground_truth_path=gt,
        baseline_dir=args.baseline_dir,
        replay_fixture=replay or Path("packages/evaluation/fixtures/replay/quiet-day.json"),
        write_report=not args.dry_run,
        attention_only=args.attention_only,
    )
    print(json.dumps(evidence.as_dict(), indent=2))
    return 0


def _run_life_script(args: argparse.Namespace) -> int:
    from personal_enigma.evaluation.life_scripts import (
        format_episode_transcript,
        resolve_script_path,
        run_life_script,
    )

    path = resolve_script_path(args.life_script)
    mode = "live" if args.live else "deterministic"
    report = run_life_script(path, mode=mode)
    print(format_episode_transcript(report))
    return 0 if report.ok else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.life_script:
        return _run_life_script(args)
    if args.composite_decomposition:
        return _run_composite_decomposition(args)
    if args.transform_diff:
        return _run_transform_diff(args)
    if args.reasoning_gate_live:
        return _run_live_gate(args)
    if args.scenario == "reasoning-gate" or args.reasoning_gate:
        return _run_reasoning_gate(args)
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
    from personal_enigma.fixtures.alex_security_overlay import resolve_load_security_overlay

    load_overlay = resolve_load_security_overlay(
        load_security_overlay=True if args.security_overlay else None
    )
    report = runner.run(
        args.scenario,
        ground_truth_path=args.ground_truth,
        observations=observations,
        run_id=args.run_id,
        write=not args.dry_run,
        scenario_version=args.scenario_version,
        load_security_overlay=load_overlay,
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
