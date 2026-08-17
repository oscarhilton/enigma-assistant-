"""Tests for support fitness scoring (Reasoning Value Gate / R04)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from personal_enigma.evaluation import EvaluationRunner
from personal_enigma.evaluation.evaluation_truth import load_evaluation_truth
from personal_enigma.evaluation.ground_truth import load_ground_truth
from personal_enigma.evaluation.metrics.support_fitness import (
    compute_support_fitness_metrics,
    score_next_action_for_contract,
)
from personal_enigma.evaluation.observations import (
    EvaluationObservations,
    NextActionObservation,
    SurfacedAlert,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ALEX_GROUND_TRUTH = REPO_ROOT / "scenarios" / "alex-v1" / "ground_truth"
SMOKE_TRUTH = Path(__file__).parent / "fixtures" / "ground_truth" / "missed_critical"


def test_december_expenses_good_action_passes() -> None:
    contract = load_evaluation_truth(ALEX_GROUND_TRUTH).support_contracts.by_scenario(
        "december-expenses"
    )
    assert contract is not None
    passed, reasons = score_next_action_for_contract(
        contract,
        observed=NextActionObservation(
            title="Gather receipts",
            action_id="gather_receipts",
            estimated_minutes=5,
            effort="light",
        ),
    )
    assert passed and reasons == ()


def test_december_expenses_poor_action_fails() -> None:
    contract = load_evaluation_truth(ALEX_GROUND_TRUTH).support_contracts.by_scenario(
        "december-expenses"
    )
    assert contract is not None
    passed, reasons = score_next_action_for_contract(
        contract,
        observed=NextActionObservation(title="Don't forget", action_id="restate_deadline_only"),
    )
    assert not passed and "poor_action_match" in reasons


def test_brunch_attention_independent_of_next_action() -> None:
    truth = load_evaluation_truth(ALEX_GROUND_TRUTH)
    at = datetime(2026, 1, 21, 13, 30, tzinfo=UTC)
    alerts = [
        SurfacedAlert(
            id="item-obligation_brunch_book",
            obligation_ids=["obligation_brunch_book"],
        )
    ]
    good = compute_support_fitness_metrics(
        truth,
        alerts=alerts,
        next_action=NextActionObservation(
            title="Prepare token review talking points",
            action_id="prepare_token_review",
            estimated_minutes=30,
        ),
        at=at,
    )
    bad = compute_support_fitness_metrics(
        truth,
        alerts=alerts,
        next_action=NextActionObservation(title="Nag", action_id="restate_deadline_only"),
        at=at,
    )
    good_cp = next(s for s in good.checkpoint_scores if s.scenario == "checkpoint-2026-01-21T13:30")
    bad_cp = next(s for s in bad.checkpoint_scores if s.scenario == "checkpoint-2026-01-21T13:30")
    assert good_cp.attention_pass and good_cp.next_action_pass
    assert bad_cp.attention_pass and not bad_cp.next_action_pass


def test_runner_includes_support_fitness_with_contracts(tmp_path: Path) -> None:
    report = EvaluationRunner(reports_root=tmp_path / "reports").run(
        "alex-v1",
        ground_truth_path=ALEX_GROUND_TRUTH,
        observations=EvaluationObservations(
            evaluated_at=datetime(2026, 1, 15, 10, 0, tzinfo=UTC),
            alerts=[
                SurfacedAlert(
                    id="item-obligation_december_expenses",
                    obligation_ids=["obligation_december_expenses"],
                )
            ],
            next_action=NextActionObservation(
                title="Gather receipts",
                action_id="gather_receipts",
                estimated_minutes=5,
            ),
        ),
        run_id="support-fitness-run",
        scenario_version="0.2.1",
    )
    assert "support_fitness" in report.metrics
    assert "## Support fitness" in (report.report_dir / "SUMMARY.md").read_text(encoding="utf-8")


def test_runner_backward_compatible_without_contracts(tmp_path: Path) -> None:
    report = EvaluationRunner(reports_root=tmp_path / "reports").run(
        "missed-critical-smoke",
        ground_truth=load_ground_truth(SMOKE_TRUTH),
        observations=EvaluationObservations(
            evaluated_at=datetime(2026, 3, 20, 11, 0, tzinfo=UTC),
            alerts=[
                SurfacedAlert(
                    id="obligation_atlas_review", obligation_ids=["obligation_atlas_review"]
                )
            ],
        ),
        run_id="no-contracts-run",
        write=False,
    )
    assert "support_fitness" not in report.metrics
