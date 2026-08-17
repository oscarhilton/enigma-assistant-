"""Demo Mode evaluation runner — aggregates metrics and writes reports."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from personal_enigma.evaluation.ab_eval import storyline_recall_under_noise
from personal_enigma.evaluation.evaluation_truth import EvaluationTruth, load_evaluation_truth
from personal_enigma.evaluation.ground_truth import (
    GroundTruthCorpus,
    load_ground_truth,
)
from personal_enigma.evaluation.metrics import (
    attention,
    cost,
    memory,
    privacy,
    retrieval,
    scale,
    support_fitness,
    suppression,
)
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
    """Aggregate attention / privacy / memory / retrieval / cost / noise metrics."""

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
        """Evaluate a scenario against ground truth + run observations."""
        obs = observations or EvaluationObservations()
        eval_truth: EvaluationTruth | None = None
        truth = ground_truth
        if truth is None:
            path = (
                Path(ground_truth_path)
                if ground_truth_path is not None
                else Path("scenarios") / scenario / "ground_truth"
            )
            if path.exists() and (path / "support_contracts.yaml").is_file():
                eval_truth = load_evaluation_truth(path)
                truth = eval_truth.ground_truth
            else:
                truth = load_ground_truth(path) if path.exists() else GroundTruthCorpus()
        elif ground_truth_path is not None:
            contract_path = Path(ground_truth_path) / "support_contracts.yaml"
            if contract_path.is_file():
                eval_truth = load_evaluation_truth(ground_truth_path)

        at = obs.evaluated_at or datetime.now(tz=UTC)
        run = run_id or _new_run_id(scenario)

        attention_m = attention.compute_attention_metrics(truth, obs.alerts, at=at)
        privacy_m = privacy.evaluate_privacy_probes(obs.privacy_probes)
        memory_m = memory.compute_memory_metrics(truth, obs.memories, at=at)
        retrieval_m = retrieval.compute_retrieval_metrics(obs.retrieval)
        cost_m = cost.compute_cost_metrics(obs.cost_events, scenario_days=self.scenario_days)

        suppression_m = suppression.compute_noise_suppression_metrics(
            truth,
            obs.alerts,
            message_count=obs.message_count,
            background_count=obs.background_count,
            noise_count=obs.noise_count,
        )
        bg_false = (
            obs.background_false_alerts
            if obs.background_false_alerts is not None
            else suppression_m.background_false_alerts
        )
        noise_false = (
            obs.noise_false_alerts
            if obs.noise_false_alerts is not None
            else suppression_m.noise_false_alerts
        )
        scale_m = scale.compute_scale_metrics(
            message_count=suppression_m.message_count,
            signals_considered=suppression_m.signals_considered,
            items_surfaced=len(obs.alerts),
            background_count=suppression_m.background_count,
            noise_count=suppression_m.noise_count,
            background_false_alerts=bg_false,
            noise_false_alerts=noise_false,
            remote_calls=obs.remote_calls,
            estimated_cost_usd=cost_m.total_usd,
            index_size_bytes=obs.index_size_bytes,
            ingest_time_ms=obs.ingest_time_ms,
            retrieval_latency_ms=obs.retrieval_latency_ms,
            recall_at_k=_as_float(
                retrieval_m.as_dict().get("recall_at_k"),
                default=1.0,
            ),
            precision=attention_m.precision,
        )

        metrics: dict[str, Any] = {
            "attention": attention_m.as_dict(),
            "privacy": privacy_m.as_dict(),
            "memory": memory_m.as_dict(),
            "retrieval": retrieval_m.as_dict(),
            "cost": cost_m.as_dict(),
            "scale": scale_m.as_dict(),
            "suppression": suppression_m.as_dict(),
        }

        if obs.spine_metrics is not None:
            ab = storyline_recall_under_noise(obs.spine_metrics, metrics)
            metrics["storyline_recall_under_noise"] = ab.as_dict()

        support_fitness_m: support_fitness.SupportFitnessMetrics | None = None
        if eval_truth is not None and eval_truth.support_contracts.contracts:
            support_fitness_m = support_fitness.compute_support_fitness_metrics(
                eval_truth,
                alerts=obs.alerts,
                next_action=obs.next_action,
                at=at,
            )
            metrics["support_fitness"] = support_fitness_m.as_dict()

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
        if not suppression_m.passed:
            failures["suppression_failures"] = [
                "background_false_alerts_per_1000="
                f"{suppression_m.background_false_alerts_per_1000:.3f} exceeds "
                f"{suppression_m.max_per_1000:.3f}"
            ]
        if support_fitness_m is not None and not support_fitness_m.passed:
            failures["support_fitness_failures"] = list(
                support_fitness_m.poor_action_failures
            ) or [
                f"attention_accuracy={support_fitness_m.attention_accuracy:.3f}",
                f"next_action_accuracy={support_fitness_m.next_action_accuracy:.3f}",
            ]

        status = _status(attention_m, privacy_m, suppression_m, support_fitness_m)
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
            "corpus_fingerprint": obs.corpus_fingerprint,
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
                suppression=metrics["suppression"],
                scale=metrics["scale"],
                storyline=metrics.get("storyline_recall_under_noise"),
                support_fitness=metrics.get("support_fitness"),
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


def _status(
    attention_m: attention.AttentionMetrics,
    privacy_m: privacy.PrivacyMetrics,
    suppression_m: suppression.NoiseSuppressionMetrics,
    support_fitness_m: support_fitness.SupportFitnessMetrics | None = None,
) -> str:
    if (
        privacy_m.direct_identifier_leaks > 0
        or privacy_m.secret_like_leaks > 0
        or privacy_m.reidentification_flags > 0
        or privacy_m.failures
    ):
        return "privacy_fail"
    if attention_m.missed:
        return "attention_miss"
    if not suppression_m.passed:
        return "suppression_fail"
    if support_fitness_m is not None and not support_fitness_m.passed:
        return "support_fitness_fail"
    return "pass"


def _as_float(value: object, *, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _new_run_id(scenario: str) -> str:
    stamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{scenario}-{stamp}-{uuid.uuid4().hex[:8]}"


__all__ = [
    "EvaluationReport",
    "EvaluationRunner",
]
