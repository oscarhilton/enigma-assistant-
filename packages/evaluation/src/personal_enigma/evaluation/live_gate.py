"""Live Reasoning Value Gate — smoke through report (R-L04–R-L08)."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from personal_enigma.evaluation.benchmark_budget import (
    HARD_CAP_USD,
    BenchmarkBudgetLedger,
    BudgetCapExceededError,
)
from personal_enigma.evaluation.evaluation_truth import EvaluationTruth, load_evaluation_truth
from personal_enigma.evaluation.failure_attribution import (
    attribute_live_disagreements,
)
from personal_enigma.evaluation.live_benchmark import (
    DISAGREEMENT_REPS,
    MAIN_REPS,
    LiveBenchmarkReport,
    LiveRepResult,
    build_live_transport,
    checkpoint_ids_from_manifest,
    load_snapshot,
    rep_stability_pct,
    run_live_benchmark,
    score_live_rep,
)
from personal_enigma.evaluation.privacy_ablation import run_live_privacy_ablation
from personal_enigma.evaluation.reasoning_value_gate import (
    collect_live_gate_evidence,
    write_live_gate_report,
)
from personal_enigma.reasoning import PaygReasoningService, ReasoningMode

LIVE_REPORT_DIR = Path("reports/reasoning-gate-live")
SMOKE_BUDGET_CAP = 0.05
MAIN_BUDGET_TARGET = 0.25
ABLATION_BUDGET_CAP = 0.15
SMOKE_REPS = 3

SmokeExpectation = Literal["must_surface", "must_suppress", "quiet"]

SMOKE_CASES: list[tuple[str, SmokeExpectation]] = [
    ("cp-2026-01-21T13:30", "must_surface"),
    ("cp-prizevault-smoke", "must_suppress"),
    ("cp-2026-01-11T11:00", "quiet"),
]

EF_MANUAL_SCENARIOS = [
    "december-expenses",
    "token-inventory-blocker",
    "checkpoint-2026-01-21T13:30",
    "parents-brunch",
    "checkout-ambiguity",
    "sam-empty-state",
    "dentist-transition",
    "q1-priorities",
    "expenses-admin-friction",
]


@dataclass
class SmokeRepOutcome:
    checkpoint_id: str
    rep: int
    passed: bool
    expectation: SmokeExpectation
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "rep": self.rep,
            "passed": self.passed,
            "expectation": self.expectation,
            "error": self.error,
        }


@dataclass
class SmokeGateReport:
    passed: bool
    outcomes: list[SmokeRepOutcome] = field(default_factory=list)
    stop_reason: str | None = None
    total_cost_usd: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "outcomes": [o.as_dict() for o in self.outcomes],
            "stop_reason": self.stop_reason,
            "total_cost_usd": self.total_cost_usd,
            "cases_required": "3/3 unanimous per case",
        }


def _attention_pass(metrics: object) -> bool:
    return getattr(metrics, "attention_accuracy", 0.0) >= 1.0


def score_smoke_rep(result: LiveRepResult, expectation: SmokeExpectation) -> bool:
    if result.parse_error or result.schema_error or result.privacy_error:
        return False
    metrics = result.metrics
    if expectation == "must_surface":
        return metrics.top3_critical_recall >= 1.0 and _attention_pass(metrics)
    if expectation == "must_suppress":
        return metrics.suppression_accuracy >= 1.0
    if expectation == "quiet":
        return metrics.suppression_accuracy >= 1.0 and metrics.attention_accuracy >= 1.0
    return False


def run_smoke_gate(
    truth: EvaluationTruth,
    *,
    baseline_dir: str | Path,
    live: bool,
    ledger: BenchmarkBudgetLedger | None = None,
) -> SmokeGateReport:
    ledger = ledger or BenchmarkBudgetLedger(
        hard_cap_usd=SMOKE_BUDGET_CAP, audit_dir=LIVE_REPORT_DIR, audit_filename="smoke-audit.jsonl"
    )
    report = SmokeGateReport(passed=True)
    root = Path(baseline_dir)

    for checkpoint_id, expectation in SMOKE_CASES:
        snapshot = load_snapshot(root, checkpoint_id)
        case_passes = 0
        for rep in range(SMOKE_REPS):
            transport = build_live_transport(
                live=live, ledger=ledger, phase="smoke", checkpoint_id=checkpoint_id
            )
            service = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=transport)
            try:
                result = score_live_rep(snapshot, truth, service=service, rep=rep)
            except BudgetCapExceededError as exc:
                report.passed = False
                report.stop_reason = str(exc)
                report.outcomes.append(
                    SmokeRepOutcome(checkpoint_id, rep, False, expectation, str(exc))
                )
                report.total_cost_usd = ledger.cumulative_usd
                return report

            passed = score_smoke_rep(result, expectation)
            error = (
                result.parse_error
                or result.schema_error
                or result.privacy_error
                or (None if passed else f"expectation {expectation} not met")
            )
            if result.parse_error:
                report.passed = False
                report.stop_reason = f"parse fail at {checkpoint_id} rep {rep}"
                report.outcomes.append(
                    SmokeRepOutcome(checkpoint_id, rep, False, expectation, error)
                )
                report.total_cost_usd = ledger.cumulative_usd
                return report
            if result.schema_error:
                report.passed = False
                report.stop_reason = f"schema fail at {checkpoint_id} rep {rep}"
                report.outcomes.append(
                    SmokeRepOutcome(checkpoint_id, rep, False, expectation, error)
                )
                report.total_cost_usd = ledger.cumulative_usd
                return report
            if result.privacy_error:
                report.passed = False
                report.stop_reason = f"privacy fail at {checkpoint_id} rep {rep}"
                report.outcomes.append(
                    SmokeRepOutcome(checkpoint_id, rep, False, expectation, error)
                )
                report.total_cost_usd = ledger.cumulative_usd
                return report

            report.outcomes.append(
                SmokeRepOutcome(checkpoint_id, rep, passed, expectation, error)
            )
            if passed:
                case_passes += 1
            else:
                report.passed = False
                report.stop_reason = (
                    f"{checkpoint_id} rep {rep} failed ({case_passes}/{SMOKE_REPS} so far)"
                )

        if case_passes != SMOKE_REPS:
            report.passed = False
            report.stop_reason = report.stop_reason or (
                f"{checkpoint_id} not unanimous {SMOKE_REPS}/{SMOKE_REPS} "
                f"(got {case_passes}/{SMOKE_REPS})"
            )
            report.total_cost_usd = ledger.cumulative_usd
            return report

    report.total_cost_usd = ledger.cumulative_usd
    return report


def select_disagreement_checkpoints(
    benchmark: LiveBenchmarkReport,
) -> list[str]:
    selected: list[str] = []
    by_a = {r.checkpoint_id: r for r in benchmark.arm_a}
    for cp_id, reps in benchmark.arm_b_reps.items():
        if cp_id not in by_a:
            continue
        a_pass = _attention_pass(by_a[cp_id].metrics)
        b_passes = [_attention_pass(r.metrics) for r in reps]
        unstable = rep_stability_pct(reps) < 1.0
        b_majority = sum(b_passes) >= (len(b_passes) // 2 + 1)
        if a_pass != b_majority or unstable:
            selected.append(cp_id)
    return selected


def select_ablation_checkpoints(
    benchmark: LiveBenchmarkReport, *, limit: int = 10
) -> list[str]:
    scored: list[tuple[float, str]] = []
    by_a = {r.checkpoint_id: r for r in benchmark.arm_a}
    for cp_id, reps in benchmark.arm_b_reps.items():
        if cp_id not in by_a or not reps:
            continue
        a_pass = _attention_pass(by_a[cp_id].metrics)
        b_passes = [_attention_pass(r.metrics) for r in reps]
        b_majority = sum(b_passes) >= (len(b_passes) // 2 + 1)
        disagree = float(a_pass != b_majority)
        stability = rep_stability_pct(reps)
        conf_penalty = 1.0 - stability
        scored.append((disagree + conf_penalty, cp_id))
    scored.sort(reverse=True)
    return [cp_id for _, cp_id in scored[:limit]]


def run_disagreement_deep_dive(
    truth: EvaluationTruth,
    *,
    baseline_dir: str | Path,
    main_benchmark: LiveBenchmarkReport,
    live: bool,
    ledger: BenchmarkBudgetLedger,
) -> dict[str, Any]:
    checkpoint_ids = select_disagreement_checkpoints(main_benchmark)
    if not checkpoint_ids:
        payload = {"checkpoint_ids": [], "attributions": [], "narrative": "No disagreements."}
        _write_json(LIVE_REPORT_DIR / "disagreements.json", payload)
        return payload

    transport = build_live_transport(live=live, ledger=ledger, phase="disagreements")
    report = run_live_benchmark(
        truth,
        baseline_dir=baseline_dir,
        checkpoint_ids=checkpoint_ids,
        transport=transport,
        phase="disagreements",
        reps=DISAGREEMENT_REPS,
        ledger=ledger,
    )
    root = Path(baseline_dir)
    snapshots = {
        cp_id: load_snapshot(root, cp_id) for cp_id in checkpoint_ids
    }
    arm_a = [r for r in main_benchmark.arm_a if r.checkpoint_id in checkpoint_ids]
    attributions = attribute_live_disagreements(
        snapshots,
        truth,
        arm_a_results=arm_a,
        arm_b_reps=report.arm_b_reps,
    )
    payload = {
        "checkpoint_ids": checkpoint_ids,
        "reps": DISAGREEMENT_REPS,
        "attributions": [a.as_dict() for a in attributions],
        "benchmark": report.as_dict(),
        "narrative": (
            "Deep-dive on A≠B or unstable-B checkpoints "
            f"({len(checkpoint_ids)} cases × {DISAGREEMENT_REPS} reps)."
        ),
    }
    _write_json(LIVE_REPORT_DIR / "disagreements.json", payload)
    return payload


def export_manual_next_action_scenarios(
    truth: EvaluationTruth,
    *,
    output_dir: Path = LIVE_REPORT_DIR,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "next-action-manual-scenarios.csv"
    md_path = output_dir / "next-action-manual-scenarios.md"
    rows: list[dict[str, str]] = []
    for contract in truth.support_contracts.contracts:
        if contract.scenario not in EF_MANUAL_SCENARIOS:
            continue
        cp = contract.next_action_checkpoint
        rows.append(
            {
                "scenario": contract.scenario,
                "obligation_id": contract.obligation_id or "",
                "good_next_actions": "|".join(contract.support.good_next_actions),
                "poor_actions": "|".join(contract.support.poor_actions),
                "expected_title": cp.expected.title if cp else "",
                "expected_action_id": cp.expected.action_id if cp and cp.expected.action_id else "",
                "manual_score": "",
                "notes": "",
            }
        )
    if not rows:
        for contract in truth.support_contracts.contracts[:8]:
            cp = contract.next_action_checkpoint
            rows.append(
                {
                    "scenario": contract.scenario,
                    "obligation_id": contract.obligation_id or "",
                    "good_next_actions": "|".join(contract.support.good_next_actions),
                    "poor_actions": "|".join(contract.support.poor_actions),
                    "expected_title": cp.expected.title if cp else "",
                    "expected_action_id": (
                        cp.expected.action_id if cp and cp.expected.action_id else ""
                    ),
                    "manual_score": "",
                    "notes": "",
                }
            )

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    md_lines = [
        "# Next Action manual scoring export",
        "",
        "Score LLM `next_action` against good/poor tokens — **no LLM-as-judge**.",
        "",
        "| Scenario | Expected | Good tokens | Poor tokens | Manual score |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        md_lines.append(
            f"| {row['scenario']} | {row['expected_title']} | "
            f"{row['good_next_actions']} | {row['poor_actions']} | |"
        )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return csv_path, md_path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _is_live_enabled(live_flag: bool) -> bool:
    return live_flag and bool(os.environ.get("FIREWORKS_API_KEY"))


@dataclass
class LiveGateRunResult:
    smoke: SmokeGateReport | None = None
    main: LiveBenchmarkReport | None = None
    disagreements: dict[str, Any] | None = None
    ablation: dict[str, Any] | None = None
    evidence: Any = None
    manual_exports: tuple[Path, Path] | None = None
    blocked: bool = False
    block_reason: str | None = None


def run_live_gate(
    *,
    ground_truth_path: str | Path,
    baseline_dir: str | Path = Path("packages/evaluation/fixtures/baselines/arm-a"),
    phase: Literal["smoke", "main", "disagreements", "ablation", "report", "all"] = "all",
    smoke_only: bool = False,
    live: bool = False,
    write_report: bool = True,
) -> LiveGateRunResult:
    truth = load_evaluation_truth(ground_truth_path)
    live_enabled = _is_live_enabled(live)
    result = LiveGateRunResult()
    ledger = BenchmarkBudgetLedger(
        hard_cap_usd=HARD_CAP_USD,
        audit_dir=LIVE_REPORT_DIR,
    )
    LIVE_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if phase in {"smoke", "all"} or smoke_only:
        result.smoke = run_smoke_gate(
            truth, baseline_dir=baseline_dir, live=live_enabled, ledger=ledger
        )
        _write_json(LIVE_REPORT_DIR / "smoke.json", result.smoke.as_dict())
        if not result.smoke.passed:
            result.blocked = True
            result.block_reason = result.smoke.stop_reason
            if smoke_only or phase == "smoke":
                return result

    if smoke_only:
        return result

    if phase in {"main", "all"} and not result.blocked:
        cp_ids = checkpoint_ids_from_manifest(baseline_dir)
        transport = build_live_transport(live=live_enabled, ledger=ledger, phase="main")
        try:
            result.main = run_live_benchmark(
                truth,
                baseline_dir=baseline_dir,
                checkpoint_ids=cp_ids,
                transport=transport,
                phase="main",
                reps=MAIN_REPS,
                ledger=ledger,
            )
        except BudgetCapExceededError as exc:
            result.blocked = True
            result.block_reason = str(exc)
            return result
        _write_json(LIVE_REPORT_DIR / "main-benchmark.json", result.main.as_dict())
        if ledger.cumulative_usd > MAIN_BUDGET_TARGET and live_enabled:
            pass  # informational — hard cap still enforced by ledger

    if phase in {"disagreements", "all"} and result.main and not result.blocked:
        result.disagreements = run_disagreement_deep_dive(
            truth,
            baseline_dir=baseline_dir,
            main_benchmark=result.main,
            live=live_enabled,
            ledger=ledger,
        )

    if phase in {"ablation", "all"} and result.main and not result.blocked:
        ablation_cap = BenchmarkBudgetLedger(
            hard_cap_usd=min(HARD_CAP_USD, ledger.cumulative_usd + ABLATION_BUDGET_CAP),
            audit_dir=LIVE_REPORT_DIR,
            cumulative_usd=ledger.cumulative_usd,
            records=list(ledger.records),
        )
        subset = select_ablation_checkpoints(result.main, limit=10)
        ablation_report = run_live_privacy_ablation(
            truth,
            baseline_dir=baseline_dir,
            checkpoint_ids=subset,
            live=live_enabled,
            ledger=ablation_cap,
        )
        result.ablation = ablation_report.as_dict()
        _write_json(LIVE_REPORT_DIR / "ablation.json", result.ablation)
        ledger.cumulative_usd = ablation_cap.cumulative_usd

    if phase in {"report", "all"} and result.main and not result.blocked:
        ablation = result.ablation or {}
        disagreements = result.disagreements or {}
        attributions = disagreements.get("attributions", [])
        result.manual_exports = export_manual_next_action_scenarios(truth)
        result.evidence = collect_live_gate_evidence(
            truth,
            main=result.main,
            ablation=ablation,
            attributions=attributions,
            ledger=ledger,
            live=live_enabled,
        )
        if write_report:
            write_live_gate_report(result.evidence)

    return result


__all__ = [
    "ABLATION_BUDGET_CAP",
    "LIVE_REPORT_DIR",
    "MAIN_BUDGET_TARGET",
    "SMOKE_BUDGET_CAP",
    "SMOKE_CASES",
    "SMOKE_REPS",
    "LiveGateRunResult",
    "SmokeGateReport",
    "export_manual_next_action_scenarios",
    "run_disagreement_deep_dive",
    "run_live_gate",
    "run_smoke_gate",
    "select_ablation_checkpoints",
    "select_disagreement_checkpoints",
]
