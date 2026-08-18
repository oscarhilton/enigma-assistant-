"""Tests for production attention context builder (R-L09)."""

from __future__ import annotations

from pathlib import Path

from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
from personal_enigma.evaluation.llm_benchmark import (
    snapshot_to_context_dict,
    snapshot_to_production_transformed,
)
from personal_enigma.reasoning.privacy_gate import assert_remote_safe
from personal_enigma.transformation import DefaultEnigmaTransformer

FIXED_HMAC_KEY = b"golden-test-hmac-key"
BASELINES = (
    Path(__file__).resolve().parents[1] / "fixtures" / "baselines" / "arm-a"
)


def test_production_transform_passes_privacy_gate() -> None:
    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-19T10:00.json")
    ctx = snapshot_to_production_transformed(snap)
    assert ctx.metadata["context_mode"] == "evaluation_transformed_v2"
    assert_remote_safe(ctx)
    assert "Elena" not in ctx.summary
    token_blocked = [
        r for r in ctx.relations if r.subject == "TASK_TOKEN_AUDIT" and r.type == "BLOCKED_BY"
    ]
    assert token_blocked and token_blocked[0].state == "resolved"


def test_default_transformer_matches_evaluation_production_path() -> None:
    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-19T10:00.json")
    transformer = DefaultEnigmaTransformer(hmac_key=FIXED_HMAC_KEY, allow_remote=True)
    from personal_enigma.transformation import candidate_input_from_observation

    direct = transformer.build_remote_attention_context(
        checkpoint_id=snap.checkpoint_id,
        checkpoint_at=snap.at,
        candidates=[candidate_input_from_observation(c) for c in snap.candidate_set[:5]],
        context_mode="production",
    )
    eval_ctx = snapshot_to_production_transformed(snap)
    assert direct.relations == eval_ctx.relations
    assert "Elena" not in direct.summary


def test_judge_context_candidate_titles_are_pseudonymised() -> None:
    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-19T10:00.json")
    ctx = snapshot_to_context_dict(snap)
    blob = str(ctx)
    assert "Elena" not in blob
    assert "Sam" not in blob
