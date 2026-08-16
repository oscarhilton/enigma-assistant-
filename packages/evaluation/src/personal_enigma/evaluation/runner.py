"""Demo Mode evaluation runner — aggregates metrics and writes reports."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from personal_enigma.evaluation.ground_truth import (
    GroundTruthCorpus,
    load_ground_truth,
)
from personal_enigma.evaluation.metrics import attention, cost, memory, privacy, retrieval
from personal_enigma.evaluation.observations import EvaluationObservations
from personal_enigma.evaluation.report import render_summary_markdown, write_report


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Complete scenario evaluation report (in-memory + on-disk paths)."""

    scenario: str
    run_id: str
    status: str
    metrics: dict[str, Any] = field(default_factory=dict)
    failures: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    report_dir: Path | None = None


class EvaluationRunner:
    """Aggregate attention / privacy / memory / retrieval / cost metrics."""

    def __init__(
        self,
        *,
        reports_root: str | Path = "reports",
        scenario_days: float = 1.0,
    ) -> None:
        self.reports_root = Path(reports_root)
        self.scenario_days = scenario_days

    def run(
        self,
        scenario: str,
        *,
        ground_truth: GroundTruthCorpus | None = None,
        ground_truth_path: str | Path | None = None,
        observations: EvaluationObservations | None = None,
        run_id: str | None = None,
        write: bool = True,
        scenario_version: str = "0.0.0",
    ) -> EvaluationReport:
        """Evaluate a scenario against ground truth + run observations.

        When ``ground_truth`` / observations are omitted, loads truth from
        ``ground_truth_path`` (or ``scenarios/<scenario>/ground_truth``) and
        uses empty observations (missed-critical detection still runs).
        """
        obs = observations or EvaluationObservations()
        truth = ground_truth
        if truth is None:
            path = (
                Path(ground_truth_path)
                if ground_truth_path is not None
                else Path("scenarios") / scenario / "ground_truth"
            )
            truth = load_ground_truth(path) if path.exists() else GroundTruthCorpus()

        at = obs.evaluated_at or datetime.now(tz=UTC)
        run = run_id or _new_run_id(scenario)

        attention_m = attention.compute_attention_metrics(truth, obs.alerts, at=at)
        privacy_m = privacy.evaluate_privacy_probes(obs.privacy_probes)
        memory_m = memory.compute_memory_metrics(truth, obs.memories, at=at)
        retrieval_m = retrieval.compute_retrieval_metrics(obs.retrieval)
        cost_m = cost.compute_cost_metrics(obs.cost_events, scenario_days=self.scenario_days)

        metrics: dict[str, Any] = {
            "attention": attention_m.as_dict(),
            "privacy": privacy_m.as_dict(),
            "memory": memory_m.as_dict(),
            "retrieval": retrieval_m.as_dict(),
            "cost": cost_m.as_dict(),
        }

        failures: dict[str, Any] = {
            "missed_obligations": [
                {
                    "obligation_id": m.obligation_id,
                    "description": m.description,
                    "importance": m.importance,
                    "reason": m.reason,
                }
                for m in attention_m.missed
            ],
            "privacy_failures": list(privacy_m.failures),
        }

        status = _status(attention_m, privacy_m)
        summary = {
            "run_id": run,
            "scenario": scenario,
            "scenario_version": scenario_version,
            "status": status,
            "git_commit": obs.git_commit,
            "provider": obs.provider,
            "model": obs.model,
            "prompt_versions": dict(obs.prompt_versions),
            "privacy_policy_version": obs.privacy_policy_version,
            "evaluated_at": at.isoformat(),
            "environment": "demo",
        }

        timeline = {
            "evaluated_at": at.isoformat(),
            "alert_count": len(obs.alerts),
            "alerts": [
                {
                    "id": a.id,
                    "obligation_ids": list(a.obligation_ids),
                    "duplicate_of": a.duplicate_of,
                    "resolved_underlying": a.resolved_underlying,
                    "surfaced_at": a.surfaced_at.isoformat() if a.surfaced_at else None,
                }
                for a in obs.alerts
            ],
        }

        report_dir: Path | None = None
        if write:
            report_dir = self.reports_root / run
            markdown = render_summary_markdown(
                run_id=run,
                scenario=scenario,
                status=status,
                attention=metrics["attention"],
                privacy=metrics["privacy"],
                cost=metrics["cost"],
            )
            write_report(
                report_dir,
                summary=summary,
                metrics=metrics,
                failures=failures,
                timeline=timeline,
                privacy={
                    **metrics["privacy"],
                    "failures": privacy_m.failures,
                },
                cost=metrics["cost"],
                markdown=markdown,
            )

        return EvaluationReport(
            scenario=scenario,
            run_id=run,
            status=status,
            metrics=metrics,
            failures=failures,
            summary=summary,
            report_dir=report_dir,
        )


def _status(attention_m: attention.AttentionMetrics, privacy_m: privacy.PrivacyMetrics) -> str:
    if privacy_m.direct_identifier_leaks > 0:
        return "privacy_fail"
    if attention_m.missed:
        return "attention_miss"
    return "pass"


def _new_run_id(scenario: str) -> str:
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{scenario}-{stamp}-{uuid.uuid4().hex[:8]}"


__all__ = [
    "EvaluationReport",
    "EvaluationRunner",
]
