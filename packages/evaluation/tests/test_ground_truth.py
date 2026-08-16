"""Tests for developer-only ground-truth models and missed-obligation detection."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from personal_enigma.evaluation.ground_truth import (
    GroundTruthValidationError,
    detect_missed_obligations,
    load_ground_truth,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ALEX_GROUND_TRUTH = REPO_ROOT / "scenarios" / "alex-v1" / "ground_truth"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ground_truth"


def test_load_alex_schema_example() -> None:
    corpus = load_ground_truth(ALEX_GROUND_TRUTH)
    assert len(corpus.obligations) >= 1
    atlas = corpus.obligation_by_id("obligation_atlas_review")
    assert atlas is not None
    assert atlas.importance == "high"
    assert atlas.beneficiary == "maya"
    assert corpus.window_for("obligation_atlas_review") is not None
    assert any(c.id == "commitment_atlas_review" for c in corpus.commitments)
    assert any(m.id == "checkpoint-2026-03-31" for m in corpus.memory_checkpoints)


def test_missed_critical_obligation_is_detected() -> None:
    corpus = load_ground_truth(FIXTURES / "missed_critical")
    # Attention never surfaced the obligation after the window opened
    missed = detect_missed_obligations(
        corpus,
        surfaced_obligation_ids=[],
        at=datetime(2026, 3, 20, 13, 0, tzinfo=UTC),
    )
    assert len(missed) == 1
    assert missed[0].obligation_id == "obligation_atlas_review"
    assert "not surfaced" in missed[0].reason


def test_surfaced_obligation_is_not_missed(tmp_path: Path) -> None:
    truth_dir = tmp_path / "ground_truth"
    truth_dir.mkdir()
    (truth_dir / "truth.yaml").write_text(
        """
obligations:
  - id: obligation_atlas_review
    description: review Atlas proposal
    created_at: "2026-03-17T11:14:00Z"
    importance: critical
    status_timeline:
      - at: "2026-03-17T11:14:00Z"
        status: open
attention_windows:
  - obligation_id: obligation_atlas_review
    earliest: "2026-03-19T09:00:00Z"
    latest: "2026-03-20T12:00:00Z"
""",
        encoding="utf-8",
    )
    corpus = load_ground_truth(truth_dir)
    missed = detect_missed_obligations(
        corpus,
        surfaced_obligation_ids={"obligation_atlas_review"},
        at=datetime(2026, 3, 20, 13, 0, tzinfo=UTC),
    )
    assert missed == []


def test_before_window_not_missed(tmp_path: Path) -> None:
    truth_dir = tmp_path / "ground_truth"
    truth_dir.mkdir()
    (truth_dir / "truth.yaml").write_text(
        """
obligations:
  - id: obligation_atlas_review
    description: review Atlas proposal
    created_at: "2026-03-17T11:14:00Z"
    importance: high
attention_windows:
  - obligation: obligation_atlas_review
    earliest: "2026-03-19T09:00:00Z"
    latest: "2026-03-20T12:00:00Z"
""",
        encoding="utf-8",
    )
    corpus = load_ground_truth(truth_dir)
    missed = detect_missed_obligations(
        corpus,
        surfaced_obligation_ids=[],
        at=datetime(2026, 3, 18, 12, 0, tzinfo=UTC),
    )
    assert missed == []


def test_invalid_attention_window_fails_validation(tmp_path: Path) -> None:
    truth_dir = tmp_path / "ground_truth"
    truth_dir.mkdir()
    (truth_dir / "bad.yaml").write_text(
        """
obligations:
  - id: obligation_x
    description: broken window
    created_at: "2026-03-01T00:00:00Z"
    importance: high
attention_windows:
  - obligation: obligation_x
    earliest: "2026-03-20T12:00:00Z"
    latest: "2026-03-19T09:00:00Z"
""",
        encoding="utf-8",
    )
    with pytest.raises(GroundTruthValidationError) as exc_info:
        load_ground_truth(truth_dir)
    assert any("earliest" in err and "latest" in err for err in exc_info.value.errors)


def test_unknown_obligation_ref_fails(tmp_path: Path) -> None:
    truth_dir = tmp_path / "ground_truth"
    truth_dir.mkdir()
    (truth_dir / "bad.yaml").write_text(
        """
obligations:
  - id: obligation_real
    description: real
    created_at: "2026-03-01T00:00:00Z"
attention_windows:
  - obligation: obligation_missing
    earliest: "2026-03-19T09:00:00Z"
    latest: "2026-03-20T12:00:00Z"
""",
        encoding="utf-8",
    )
    with pytest.raises(GroundTruthValidationError) as exc_info:
        load_ground_truth(truth_dir)
    assert any("unknown obligation" in err for err in exc_info.value.errors)


def test_invalid_importance_fails(tmp_path: Path) -> None:
    truth_file = tmp_path / "one.yaml"
    truth_file.write_text(
        """
kind: obligation
id: obligation_bad
description: bad importance
created_at: "2026-03-01T00:00:00Z"
importance: urgent
""",
        encoding="utf-8",
    )
    with pytest.raises(GroundTruthValidationError):
        load_ground_truth(truth_file)


def test_commitment_kind_field_is_not_document_discriminator(tmp_path: Path) -> None:
    """``kind: inferred`` is a CommitmentTruth field, not a document type."""
    truth_dir = tmp_path / "ground_truth"
    truth_dir.mkdir()
    (truth_dir / "commitment.yaml").write_text(
        """
id: commitment_deck
description: Send Q2 deck to Maya
kind: inferred
created_at: "2026-03-02T09:00:00Z"
due_at: "2026-03-04T17:00:00Z"
""",
        encoding="utf-8",
    )
    corpus = load_ground_truth(truth_dir)
    assert len(corpus.commitments) == 1
    assert corpus.commitments[0].kind.value == "inferred"
    assert corpus.obligations == []


def test_invalid_obligation_status_fails(tmp_path: Path) -> None:
    truth_file = tmp_path / "bad_status.yaml"
    truth_file.write_text(
        """
kind: obligation
id: obligation_typo
description: typo status
created_at: "2026-03-01T00:00:00Z"
status_timeline:
  - at: "2026-03-01T00:00:00Z"
    status: opne
""",
        encoding="utf-8",
    )
    with pytest.raises(GroundTruthValidationError) as exc_info:
        load_ground_truth(truth_file)
    assert any("invalid status" in err for err in exc_info.value.errors)


def test_spec_shaped_singular_wrappers(tmp_path: Path) -> None:
    truth_dir = tmp_path / "ground_truth"
    truth_dir.mkdir()
    (truth_dir / "obligation.yaml").write_text(
        """
id: obligation_atlas_review
actor: alex
beneficiary: maya
description: review Atlas proposal
created_at: "2026-03-17T11:14:00"
due_at: "2026-03-20T15:00:00"
importance: high
status_timeline:
  - at: "2026-03-17"
    status: open
""",
        encoding="utf-8",
    )
    (truth_dir / "attention.yaml").write_text(
        """
attention_expectation:
  obligation: obligation_atlas_review
  earliest: "2026-03-19T09:00"
  ideal: "2026-03-20T09:30"
  latest: "2026-03-20T12:00"
  minimum_priority: 4
""",
        encoding="utf-8",
    )
    (truth_dir / "checkpoint.yaml").write_text(
        """
checkpoint:
  at: "2026-03-31"
  expected_memories:
    - maya_is_manager
    - atlas_is_active_project
""",
        encoding="utf-8",
    )
    corpus = load_ground_truth(truth_dir)
    assert corpus.obligation_by_id("obligation_atlas_review") is not None
    assert corpus.window_for("obligation_atlas_review") is not None
    assert len(corpus.memory_checkpoints) == 1
