"""Demo checkpoint listing and semantic bootstrap."""

from __future__ import annotations

from personal_enigma.fixtures.demo_checkpoints import (
    bootstrap_semantic_inputs,
    list_demo_checkpoints,
    load_checkpoint_snapshot,
    load_semantic_inputs,
    resolve_semantic_inputs,
)


def test_list_demo_checkpoints_exposes_arm_a_span() -> None:
    rows = list_demo_checkpoints()
    ids = [row["id"] for row in rows]
    assert len(ids) == 20
    assert ids[0] == "cp-2026-01-08T15:00"
    assert ids[-1] == "cp-2026-01-25T17:00"


def test_curated_semantics_preferred_for_milestones() -> None:
    snapshot = load_checkpoint_snapshot("cp-2026-01-19T10:00")
    curated = load_semantic_inputs("cp-2026-01-19T10:00")
    resolved = resolve_semantic_inputs("cp-2026-01-19T10:00", snapshot)
    assert curated
    assert resolved == curated


def test_bootstrap_fills_non_milestone_checkpoints() -> None:
    snapshot = load_checkpoint_snapshot("cp-2026-01-08T15:00")
    assert load_semantic_inputs("cp-2026-01-08T15:00") == {}
    semantics = bootstrap_semantic_inputs(snapshot)
    assert semantics
    assert all(row.reason_codes == ["DEMO_BOOTSTRAP"] for row in semantics.values())
