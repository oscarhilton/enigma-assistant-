"""Support fitness metrics for Demo Mode evaluation (Reasoning Value Gate / R04, R-L02)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from personal_enigma.evaluation.evaluation_truth import EvaluationTruth
from personal_enigma.evaluation.ground_truth import CRITICAL_IMPORTANCE
from personal_enigma.evaluation.observations import NextActionObservation, SurfacedAlert
from personal_enigma.evaluation.support_contract import AttentionBehaviour, SupportContract

_TOP_N = 3


class RescueRegressionOutcome(StrEnum):
    """Arm A vs Arm B per-checkpoint outcome (R-L02)."""

    RESCUE = "RESCUE"  # A wrong → B right
    REGRESSION = "REGRESSION"  # A right → B wrong
    AGREEMENT = "AGREEMENT"  # both right
    SHARED_FAILURE = "SHARED_FAILURE"  # both wrong


@dataclass(frozen=True, slots=True)
class ContractCheckpointScore:
    scenario: str
    at: str
    attention_pass: bool
    next_action_pass: bool | None
    attention_reason_codes: tuple[str, ...] = ()
    next_action_reason_codes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "at": self.at,
            "attention_pass": self.attention_pass,
            "next_action_pass": self.next_action_pass,
            "attention_reason_codes": list(self.attention_reason_codes),
            "next_action_reason_codes": list(self.next_action_reason_codes),
        }


@dataclass(frozen=True, slots=True)
class AttentionFitnessMetrics:
    suppression_accuracy: float
    top3_critical_recall: float
    top1_critical_recall: float
    attention_accuracy: float
    contracts_scored: int
    passed: bool
    checkpoint_scores: tuple[ContractCheckpointScore, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "suppression_accuracy": self.suppression_accuracy,
            "top3_critical_recall": self.top3_critical_recall,
            "top1_critical_recall": self.top1_critical_recall,
            "attention_accuracy": self.attention_accuracy,
            "contracts_scored": self.contracts_scored,
            "passed": self.passed,
            "checkpoint_scores": [s.as_dict() for s in self.checkpoint_scores],
        }


@dataclass(frozen=True, slots=True)
class NextActionFitnessMetrics:
    actionability: float
    task_size_fit: float
    friction_reduction: float
    timing_fit: float
    next_action_accuracy: float
    next_action_checkpoints_scored: int
    passed: bool
    poor_action_failures: tuple[str, ...] = ()
    checkpoint_scores: tuple[ContractCheckpointScore, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "actionability": self.actionability,
            "task_size_fit": self.task_size_fit,
            "friction_reduction": self.friction_reduction,
            "timing_fit": self.timing_fit,
            "next_action_accuracy": self.next_action_accuracy,
            "next_action_checkpoints_scored": self.next_action_checkpoints_scored,
            "passed": self.passed,
            "poor_action_failures": list(self.poor_action_failures),
            "checkpoint_scores": [s.as_dict() for s in self.checkpoint_scores],
        }


@dataclass(frozen=True, slots=True)
class SupportFitnessMetrics:
    actionability: float
    task_size_fit: float
    friction_reduction: float
    timing_fit: float
    suppression_accuracy: float
    top3_critical_recall: float
    top1_critical_recall: float
    attention_accuracy: float
    next_action_accuracy: float
    contracts_scored: int
    next_action_checkpoints_scored: int
    passed: bool
    poor_action_failures: tuple[str, ...] = ()
    checkpoint_scores: list[ContractCheckpointScore] = field(default_factory=list)
    attention: AttentionFitnessMetrics | None = None
    next_action: NextActionFitnessMetrics | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "actionability": self.actionability,
            "task_size_fit": self.task_size_fit,
            "friction_reduction": self.friction_reduction,
            "timing_fit": self.timing_fit,
            "suppression_accuracy": self.suppression_accuracy,
            "top3_critical_recall": self.top3_critical_recall,
            "top1_critical_recall": self.top1_critical_recall,
            "attention_accuracy": self.attention_accuracy,
            "next_action_accuracy": self.next_action_accuracy,
            "contracts_scored": self.contracts_scored,
            "next_action_checkpoints_scored": self.next_action_checkpoints_scored,
            "passed": self.passed,
            "poor_action_failures": list(self.poor_action_failures),
            "checkpoint_scores": [s.as_dict() for s in self.checkpoint_scores],
        }
        if self.attention is not None:
            payload["attention"] = self.attention.as_dict()
        if self.next_action is not None:
            payload["next_action"] = self.next_action.as_dict()
        return payload


@dataclass(frozen=True, slots=True)
class RescueRegressionCase:
    checkpoint_id: str
    dimension: Literal["attention", "next_action"]
    outcome: RescueRegressionOutcome

    def as_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "dimension": self.dimension,
            "outcome": self.outcome.value,
        }


def _normalize_at(when: datetime) -> datetime:
    if when.tzinfo is None:
        return when.replace(tzinfo=UTC)
    return when


def _top_obligation_ids(alerts: Sequence[SurfacedAlert], *, n: int = _TOP_N) -> set[str]:
    ids: set[str] = set()
    for alert in alerts[:n]:
        ids.update(alert.obligation_ids)
        if alert.id.startswith("item-"):
            ids.add(alert.id.removeprefix("item-"))
    return ids


def _top1_obligation_ids(alerts: Sequence[SurfacedAlert]) -> set[str]:
    return _top_obligation_ids(alerts, n=1)


def _alert_evidence_ids(alerts: Sequence[SurfacedAlert]) -> set[str]:
    return {eid for alert in alerts for eid in alert.evidence_ids}


def _score_attention_contract(
    contract: SupportContract,
    *,
    alerts: Sequence[SurfacedAlert],
) -> tuple[bool, tuple[str, ...]]:
    behaviour = contract.attention.behaviour
    top_ids = _top_obligation_ids(alerts)
    evidence_surfaced = _alert_evidence_ids(alerts)
    obligation_id = contract.obligation_id

    if behaviour == AttentionBehaviour.MAY_SURFACE:
        return True, ()
    if behaviour == AttentionBehaviour.MUST_SURFACE:
        if obligation_id is None:
            return True, ()
        if obligation_id in top_ids:
            return True, ()
        return False, ("must_surface_missed",)
    if behaviour == AttentionBehaviour.MUST_SUPPRESS:
        if set(contract.evidence_ids) & evidence_surfaced:
            return False, ("must_suppress_violated",)
        return True, ()
    if behaviour == AttentionBehaviour.MUST_STAY_QUIET:
        if alerts:
            return False, ("must_stay_quiet_violated",)
        return True, ()
    return True, ()


def _score_next_action(
    contract: SupportContract,
    *,
    observed: NextActionObservation | None,
) -> tuple[bool, tuple[str, ...], dict[str, bool]]:
    components = {
        "actionability": False,
        "task_size_fit": True,
        "friction_reduction": False,
        "timing_fit": True,
    }
    if observed is None:
        return False, ("next_action_missing",), components
    token = observed.action_id or observed.title.strip().lower().replace(" ", "_")
    if not token:
        return False, ("next_action_not_actionable",), components
    components["actionability"] = True
    if token in contract.support.poor_actions:
        return False, ("poor_action_match",), components
    preferred = contract.support.preferred_effort
    if preferred and preferred.max_minutes and observed.estimated_minutes:
        if observed.estimated_minutes > preferred.max_minutes:
            components["task_size_fit"] = False
            return False, ("task_size_exceeded",), components
    if (
        token in contract.support.good_next_actions
        or token in contract.support.acceptable_next_actions
    ):
        components["friction_reduction"] = True
        return True, (), components
    return False, ("unknown_action_token",), components


def score_next_action_for_contract(
    contract: SupportContract, *, observed: NextActionObservation | None
) -> tuple[bool, tuple[str, ...]]:
    passed, reasons, _ = _score_next_action(contract, observed=observed)
    return passed, reasons


def compute_attention_fitness_metrics(
    truth: EvaluationTruth,
    *,
    alerts: Sequence[SurfacedAlert],
    at: datetime,
) -> AttentionFitnessMetrics:
    when = _normalize_at(at)
    active = truth.support_contracts.active_at(when)
    if not active:
        return AttentionFitnessMetrics(1, 1, 1, 1, 0, True)

    checkpoint_scores: list[ContractCheckpointScore] = []
    attention_passes = suppress_passes = suppress_total = 0
    must_surface_critical_expected = must_surface_critical_hit_top3 = (
        must_surface_critical_hit_top1
    ) = 0

    for contract in active:
        att_pass, att_reasons = _score_attention_contract(contract, alerts=alerts)
        attention_passes += int(att_pass)
        if contract.attention.behaviour in {
            AttentionBehaviour.MUST_SUPPRESS,
            AttentionBehaviour.MUST_STAY_QUIET,
        }:
            suppress_total += 1
            suppress_passes += int(att_pass)
        if (
            contract.attention.behaviour == AttentionBehaviour.MUST_SURFACE
            and contract.obligation_id
        ):
            obligation = truth.ground_truth.obligation_by_id(contract.obligation_id)
            if obligation and obligation.importance in CRITICAL_IMPORTANCE:
                must_surface_critical_expected += 1
                in_top3 = contract.obligation_id in _top_obligation_ids(alerts)
                in_top1 = contract.obligation_id in _top1_obligation_ids(alerts)
                must_surface_critical_hit_top3 += int(in_top3)
                must_surface_critical_hit_top1 += int(in_top1)
        checkpoint_scores.append(
            ContractCheckpointScore(
                contract.scenario, when.isoformat(), att_pass, None, att_reasons, ()
            )
        )

    n = len(active)
    return AttentionFitnessMetrics(
        suppression_accuracy=suppress_passes / suppress_total if suppress_total else 1.0,
        top3_critical_recall=must_surface_critical_hit_top3 / must_surface_critical_expected
        if must_surface_critical_expected
        else 1.0,
        top1_critical_recall=must_surface_critical_hit_top1 / must_surface_critical_expected
        if must_surface_critical_expected
        else 1.0,
        attention_accuracy=attention_passes / n,
        contracts_scored=n,
        passed=attention_passes == n,
        checkpoint_scores=tuple(checkpoint_scores),
    )


def compute_next_action_fitness_metrics(
    truth: EvaluationTruth,
    *,
    next_action: NextActionObservation | None,
    at: datetime,
) -> NextActionFitnessMetrics:
    when = _normalize_at(at)
    active = truth.support_contracts.active_at(when)
    if not active:
        return NextActionFitnessMetrics(1, 1, 1, 1, 1, 0, True)

    checkpoint_scores: list[ContractCheckpointScore] = []
    next_action_passes = next_action_total = 0
    actionability_hits = task_size_hits = friction_hits = timing_hits = 0
    poor_failures: list[str] = []

    for contract in active:
        cp = contract.next_action_checkpoint
        if cp and _normalize_at(cp.at) == when:
            next_action_total += 1
            na_pass, na_reasons, components = _score_next_action(contract, observed=next_action)
            next_action_passes += int(na_pass)
            actionability_hits += int(components["actionability"])
            task_size_hits += int(components["task_size_fit"])
            friction_hits += int(components["friction_reduction"])
            timing_hits += int(components["timing_fit"])
            if "poor_action_match" in na_reasons:
                poor_failures.append(contract.scenario)
            checkpoint_scores.append(
                ContractCheckpointScore(
                    contract.scenario, when.isoformat(), True, na_pass, (), na_reasons
                )
            )

    next_acc = next_action_passes / next_action_total if next_action_total else 1.0
    return NextActionFitnessMetrics(
        actionability=actionability_hits / next_action_total if next_action_total else 1.0,
        task_size_fit=task_size_hits / next_action_total if next_action_total else 1.0,
        friction_reduction=friction_hits / next_action_total if next_action_total else 1.0,
        timing_fit=timing_hits / next_action_total if next_action_total else 1.0,
        next_action_accuracy=next_acc,
        next_action_checkpoints_scored=next_action_total,
        passed=next_acc >= 1.0 and not poor_failures,
        poor_action_failures=tuple(poor_failures),
        checkpoint_scores=tuple(checkpoint_scores),
    )


def compute_support_fitness_metrics(
    truth: EvaluationTruth,
    *,
    alerts: Sequence[SurfacedAlert],
    next_action: NextActionObservation | None,
    at: datetime,
    attention_only: bool = False,
) -> SupportFitnessMetrics:
    attention_m = compute_attention_fitness_metrics(truth, alerts=alerts, at=at)
    if attention_only:
        return SupportFitnessMetrics(
            actionability=1.0,
            task_size_fit=1.0,
            friction_reduction=1.0,
            timing_fit=1.0,
            suppression_accuracy=attention_m.suppression_accuracy,
            top3_critical_recall=attention_m.top3_critical_recall,
            top1_critical_recall=attention_m.top1_critical_recall,
            attention_accuracy=attention_m.attention_accuracy,
            next_action_accuracy=1.0,
            contracts_scored=attention_m.contracts_scored,
            next_action_checkpoints_scored=0,
            passed=attention_m.passed,
            checkpoint_scores=list(attention_m.checkpoint_scores),
            attention=attention_m,
            next_action=None,
        )

    next_action_m = compute_next_action_fitness_metrics(
        truth, next_action=next_action, at=at
    )
    merged_scores: list[ContractCheckpointScore] = []
    na_by_scenario = {s.scenario: s for s in next_action_m.checkpoint_scores}
    for att_score in attention_m.checkpoint_scores:
        na_score = na_by_scenario.get(att_score.scenario)
        merged_scores.append(
            ContractCheckpointScore(
                att_score.scenario,
                att_score.at,
                att_score.attention_pass,
                na_score.next_action_pass if na_score else None,
                att_score.attention_reason_codes,
                na_score.next_action_reason_codes if na_score else (),
            )
        )

    return SupportFitnessMetrics(
        actionability=next_action_m.actionability,
        task_size_fit=next_action_m.task_size_fit,
        friction_reduction=next_action_m.friction_reduction,
        timing_fit=next_action_m.timing_fit,
        suppression_accuracy=attention_m.suppression_accuracy,
        top3_critical_recall=attention_m.top3_critical_recall,
        top1_critical_recall=attention_m.top1_critical_recall,
        attention_accuracy=attention_m.attention_accuracy,
        next_action_accuracy=next_action_m.next_action_accuracy,
        contracts_scored=attention_m.contracts_scored,
        next_action_checkpoints_scored=next_action_m.next_action_checkpoints_scored,
        passed=attention_m.passed and next_action_m.passed,
        poor_action_failures=next_action_m.poor_action_failures,
        checkpoint_scores=merged_scores,
        attention=attention_m,
        next_action=next_action_m,
    )


def classify_arm_outcome(*, arm_a_pass: bool, arm_b_pass: bool) -> RescueRegressionOutcome:
    if arm_a_pass and arm_b_pass:
        return RescueRegressionOutcome.AGREEMENT
    if not arm_a_pass and arm_b_pass:
        return RescueRegressionOutcome.RESCUE
    if arm_a_pass and not arm_b_pass:
        return RescueRegressionOutcome.REGRESSION
    return RescueRegressionOutcome.SHARED_FAILURE


def compute_rescue_regression_metrics(
    *,
    checkpoint_id: str,
    arm_a: SupportFitnessMetrics,
    arm_b: SupportFitnessMetrics,
) -> list[RescueRegressionCase]:
    cases: list[RescueRegressionCase] = []
    att_a = arm_a.attention_accuracy >= 1.0
    att_b = arm_b.attention_accuracy >= 1.0
    cases.append(
        RescueRegressionCase(
            checkpoint_id=checkpoint_id,
            dimension="attention",
            outcome=classify_arm_outcome(arm_a_pass=att_a, arm_b_pass=att_b),
        )
    )
    if arm_a.next_action_checkpoints_scored > 0 or arm_b.next_action_checkpoints_scored > 0:
        na_a = arm_a.next_action_accuracy >= 1.0
        na_b = arm_b.next_action_accuracy >= 1.0
        cases.append(
            RescueRegressionCase(
                checkpoint_id=checkpoint_id,
                dimension="next_action",
                outcome=classify_arm_outcome(arm_a_pass=na_a, arm_b_pass=na_b),
            )
        )
    return cases


def summarize_rescue_regression(cases: Sequence[RescueRegressionCase]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for case in cases:
        summary[case.outcome.value] = summary.get(case.outcome.value, 0) + 1
    return summary


__all__ = [
    "AttentionFitnessMetrics",
    "ContractCheckpointScore",
    "NextActionFitnessMetrics",
    "RescueRegressionCase",
    "RescueRegressionOutcome",
    "SupportFitnessMetrics",
    "classify_arm_outcome",
    "compute_attention_fitness_metrics",
    "compute_next_action_fitness_metrics",
    "compute_rescue_regression_metrics",
    "compute_support_fitness_metrics",
    "score_next_action_for_contract",
    "summarize_rescue_regression",
]
