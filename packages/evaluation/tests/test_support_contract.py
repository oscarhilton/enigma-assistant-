"""Tests for evaluator-only support contracts (Reasoning Value Gate / R01)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from personal_enigma.evaluation.ground_truth import GroundTruthValidationError
from personal_enigma.evaluation.support_contract import (
    AttentionBehaviour,
    load_support_contracts,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ALEX_GROUND_TRUTH = REPO_ROOT / "scenarios" / "alex-v1" / "ground_truth"
ALEX_CONTRACTS = ALEX_GROUND_TRUTH / "support_contracts.yaml"


def test_load_alex_support_contracts_has_twelve_plus_arcs() -> None:
    corpus = load_support_contracts(ALEX_CONTRACTS)
    assert len(corpus.contracts) >= 12
    scenario_ids = {c.scenario for c in corpus.contracts}
    assert "elena-parents-brunch" in scenario_ids
    assert "december-expenses" in scenario_ids
    assert "checkpoint-2026-01-21T13:30" in scenario_ids


def test_brunch_contract_links_obligation_and_window() -> None:
    corpus = load_support_contracts(ALEX_CONTRACTS)
    brunch = corpus.by_scenario("elena-parents-brunch")
    assert brunch is not None
    assert brunch.obligation_id == "obligation_brunch_book"
    assert brunch.attention.behaviour == AttentionBehaviour.MUST_SURFACE
    assert brunch.attention.minimum_priority == 5
    assert brunch.attention.window is not None
    assert brunch.is_active_at(datetime(2026, 1, 21, 10, 0, tzinfo=UTC))
    assert not brunch.is_active_at(datetime(2026, 1, 19, 7, 0, tzinfo=UTC))


def test_must_suppress_arcs_have_no_window() -> None:
    corpus = load_support_contracts(ALEX_CONTRACTS)
    suppress_ids = {
        "newsletters-promos",
        "prizzevault-junk",
        "machine-notifications",
    }
    suppress = [c for c in corpus.contracts if c.scenario in suppress_ids]
    assert len(suppress) == 3
    for contract in suppress:
        assert contract.attention.behaviour == AttentionBehaviour.MUST_SUPPRESS
        assert contract.attention.window is None
        assert contract.is_active_at(datetime(2026, 1, 15, 12, 0, tzinfo=UTC))


def test_dual_checkpoint_contract() -> None:
    corpus = load_support_contracts(ALEX_CONTRACTS)
    checkpoint = corpus.by_scenario("checkpoint-2026-01-21T13:30")
    assert checkpoint is not None
    assert checkpoint.next_action_checkpoint is not None
    na = checkpoint.next_action_checkpoint
    assert na.at == datetime(2026, 1, 21, 13, 30, tzinfo=UTC)
    assert na.expected.action_id == "prepare_token_review"
    assert na.attention_item_id == "obligation_brunch_book"


def test_active_at_filters_by_window() -> None:
    corpus = load_support_contracts(ALEX_CONTRACTS)
    when = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
    active = corpus.active_at(when)
    active_ids = {c.scenario for c in active}
    assert "december-expenses" in active_ids
    assert "newsletters-promos" in active_ids
    assert "elena-parents-brunch" not in active_ids


def test_duplicate_scenario_ids_fail(tmp_path: Path) -> None:
    path = tmp_path / "dup.yaml"
    path.write_text(
        """
support_contracts:
  - scenario: arc-a
    challenge: [distraction]
    attention: { behaviour: MUST_SUPPRESS }
    support: { good_next_actions: [suppress_newsletter] }
  - scenario: arc-a
    challenge: [distraction]
    attention: { behaviour: MUST_SUPPRESS }
    support: { good_next_actions: [suppress_newsletter] }
""",
        encoding="utf-8",
    )
    with pytest.raises(GroundTruthValidationError) as exc_info:
        load_support_contracts(path)
    assert any("duplicate" in err for err in exc_info.value.errors)


def test_invalid_behaviour_fails(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text(
        """
support_contracts:
  - scenario: arc-a
    challenge: [distraction]
    attention: { behaviour: SURFACE_ALWAYS }
    support: { good_next_actions: [suppress_newsletter] }
""",
        encoding="utf-8",
    )
    with pytest.raises(GroundTruthValidationError):
        load_support_contracts(path)


def test_load_from_directory(tmp_path: Path) -> None:
    gt_dir = tmp_path / "ground_truth"
    gt_dir.mkdir()
    (gt_dir / "support_contracts.yaml").write_text(
        """
support_contracts:
  - scenario: quiet-periods
    challenge: [task_initiation]
    attention:
      behaviour: MUST_STAY_QUIET
      window:
        start: "2026-01-10T10:00:00Z"
        end: "2026-01-11T18:00:00Z"
    support:
      good_next_actions: [suggest_rest]
""",
        encoding="utf-8",
    )
    corpus = load_support_contracts(gt_dir)
    assert len(corpus.contracts) == 1
    assert corpus.by_scenario("quiet-periods") is not None
