"""R-L09 Step 6 — transformed-context prompt wiring acceptance tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
from personal_enigma.evaluation.evaluation_truth import load_evaluation_truth
from personal_enigma.evaluation.llm_benchmark import (
    FORBIDDEN_PROMPT_MARKERS,
    build_semantic_judge_prompt,
    score_arm_b,
    serialise_transformed_context_for_judge,
    snapshot_to_full_synthetic_context,
    snapshot_to_production_transformed,
)
from personal_enigma.reasoning import PaygReasoningService, ReasoningMode
from personal_enigma.reasoning.privacy_gate import assert_remote_safe
from personal_enigma.transformation import (
    DefaultEnigmaTransformer,
    candidate_input_from_observation,
)

REPO = Path(__file__).resolve().parents[3]
GT = REPO / "scenarios" / "alex-v1" / "ground_truth"
BASELINES = Path(__file__).resolve().parents[1] / "fixtures" / "baselines" / "arm-a"
JAN19 = "cp-2026-01-19T10:00"
JAN20 = "cp-2026-01-20T11:00"
TOKEN_AUDIT_CANDIDATE = "item-obligation_token_audit"


def _token_audit_candidate(snap):
    return next(c for c in snap.candidate_set if c.id == TOKEN_AUDIT_CANDIDATE)


def test_v2_and_full_synthetic_prompts_not_byte_identical() -> None:
    snap = load_checkpoint_snapshot(BASELINES / f"{JAN19}.json")
    candidate = _token_audit_candidate(snap)
    v2_ctx = snapshot_to_production_transformed(snap)
    full_ctx = snapshot_to_full_synthetic_context(snap)
    v2_prompt = build_semantic_judge_prompt(
        v2_ctx, candidate, checkpoint_at=snap.at, snapshot=snap
    )
    full_prompt = build_semantic_judge_prompt(
        full_ctx, candidate, checkpoint_at=snap.at, snapshot=snap
    )
    assert v2_prompt != full_prompt


def test_v2_prompt_contains_privacy_safe_relations() -> None:
    snap = load_checkpoint_snapshot(BASELINES / f"{JAN19}.json")
    candidate = _token_audit_candidate(snap)
    ctx = snapshot_to_production_transformed(snap)
    assert_remote_safe(ctx)
    prompt = build_semantic_judge_prompt(
        ctx, candidate, checkpoint_at=snap.at, snapshot=snap
    )
    assert "BLOCKED_BY" in prompt
    assert "TASK_TOKEN_AUDIT" in prompt
    assert '"state": "resolved"' in prompt or '"state":"resolved"' in prompt.replace(" ", "")


def test_evaluation_and_production_share_serialisation_path() -> None:
    snap = load_checkpoint_snapshot(BASELINES / f"{JAN19}.json")
    candidate = _token_audit_candidate(snap)
    eval_ctx = snapshot_to_production_transformed(snap)
    from personal_enigma.evaluation.llm_benchmark import _EVAL_TRANSFORM_HMAC_KEY

    transformer = DefaultEnigmaTransformer(hmac_key=_EVAL_TRANSFORM_HMAC_KEY, allow_remote=True)
    prod_ctx = transformer.build_remote_attention_context(
        checkpoint_id=snap.checkpoint_id,
        checkpoint_at=snap.at,
        candidates=[candidate_input_from_observation(c) for c in snap.candidate_set[:5]],
        context_mode="production",
    )
    eval_wire = serialise_transformed_context_for_judge(
        eval_ctx,
        candidate=candidate,
        checkpoint_at=snap.at,
        privacy="remote_safe",
        snapshot=snap,
    )
    prod_wire = serialise_transformed_context_for_judge(
        prod_ctx,
        candidate=candidate,
        checkpoint_at=snap.at,
        privacy="remote_safe",
        snapshot=snap,
    )
    assert eval_wire["relations"] == prod_wire["relations"]
    assert eval_wire["summary"] == prod_wire["summary"]
    assert eval_wire["entities"] == prod_wire["entities"]


def test_serialised_prompt_passes_privacy_checks() -> None:
    snap = load_checkpoint_snapshot(BASELINES / f"{JAN19}.json")
    candidate = _token_audit_candidate(snap)
    ctx = snapshot_to_production_transformed(snap)
    assert_remote_safe(ctx)
    prompt = build_semantic_judge_prompt(
        ctx, candidate, checkpoint_at=snap.at, snapshot=snap
    )
    for name in ("Elena", "Jordan", "Sam", "Maya"):
        assert name not in prompt


def test_jan19_context_json_blocked_by_resolved_causal() -> None:
    snap = load_checkpoint_snapshot(BASELINES / f"{JAN19}.json")
    candidate = _token_audit_candidate(snap)
    ctx = snapshot_to_production_transformed(snap)
    wire = serialise_transformed_context_for_judge(
        ctx,
        candidate=candidate,
        checkpoint_at=snap.at,
        privacy="remote_safe",
        snapshot=snap,
    )
    blocked = [
        r
        for r in wire["relations"]
        if r.get("type") == "BLOCKED_BY" and r.get("subject") == "TASK_TOKEN_AUDIT"
    ]
    assert blocked, wire["relations"]
    assert blocked[0]["state"] == "resolved"
    assert blocked[0].get("causal")
    blob = json.dumps(wire)
    assert "TASK_TOKEN_AUDIT" in blob
    assert "BLOCKED_BY" in blob
    assert "resolved" in blob


def test_jan20_context_json_blocked_by_resolved() -> None:
    snap = load_checkpoint_snapshot(BASELINES / f"{JAN20}.json")
    candidate = next(
        (c for c in snap.candidate_set if "token_audit" in c.id), snap.candidate_set[0]
    )
    ctx = snapshot_to_production_transformed(snap)
    wire = serialise_transformed_context_for_judge(
        ctx,
        candidate=candidate,
        checkpoint_at=snap.at,
        privacy="remote_safe",
        snapshot=snap,
    )
    relations_blob = json.dumps(wire["relations"])
    assert "BLOCKED_BY" in relations_blob
    assert "resolved" in relations_blob


def test_no_forbidden_evaluator_markers_in_payload_or_prompt() -> None:
    snap = load_checkpoint_snapshot(BASELINES / f"{JAN19}.json")
    candidate = _token_audit_candidate(snap)
    ctx = snapshot_to_production_transformed(snap)
    wire = serialise_transformed_context_for_judge(
        ctx,
        candidate=candidate,
        checkpoint_at=snap.at,
        privacy="remote_safe",
        snapshot=snap,
    )
    prompt = build_semantic_judge_prompt(
        ctx, candidate, checkpoint_at=snap.at, snapshot=snap
    )
    combined = json.dumps(wire) + prompt
    lower = combined.lower()
    for marker in FORBIDDEN_PROMPT_MARKERS:
        assert marker.lower() not in lower
    for forbidden in (
        "expected_surface_window",
        "attention_pass",
        "MUST_STAY_QUIET",
    ):
        assert forbidden.lower() not in lower


def test_invalid_experiment_on_prompt_build_failure_not_arm_a_fallback() -> None:
    truth = load_evaluation_truth(GT)
    snap = load_checkpoint_snapshot(BASELINES / f"{JAN19}.json")
    ctx = snapshot_to_production_transformed(snap)
    service = PaygReasoningService(mode=ReasoningMode.DRY_RUN)

    class _NeverCalledTransport:
        def complete(self, *, model: str, prompt: str, context):  # noqa: ANN001
            raise AssertionError("transport must not be called when prompt build fails")

    service = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=_NeverCalledTransport())

    with patch(
        "personal_enigma.evaluation.llm_benchmark.build_semantic_judge_prompt",
        side_effect=ValueError("simulated prompt_build_failed"),
    ):
        result = score_arm_b(
            snap,
            truth,
            service=service,
            context=ctx,
            judge_arm="b2",
            prompt_privacy="remote_safe",
        )

    assert result.experiment_invalid
    assert result.parse_error is not None
    assert result.metrics.top3_critical_recall != 1.0 or snap.alerts == []


def test_relations_authoritative_instruction_in_prompt() -> None:
    snap = load_checkpoint_snapshot(BASELINES / f"{JAN19}.json")
    candidate = _token_audit_candidate(snap)
    ctx = snapshot_to_production_transformed(snap)
    prompt = build_semantic_judge_prompt(
        ctx, candidate, checkpoint_at=snap.at, snapshot=snap
    )
    assert "relations[] as authoritative" in prompt.lower() or "relations[]" in prompt
