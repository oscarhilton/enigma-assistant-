"""Tests for LLM judge benchmark (R03, R-L02 judge-v1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from personal_enigma.evaluation._testing.judge_mock import (
    PerCandidateJudgeMockTransport,
    surface_expenses_json,
)
from personal_enigma.evaluation.evaluation_truth import load_evaluation_truth
from personal_enigma.evaluation.llm_benchmark import (
    FORBIDDEN_PROMPT_MARKERS,
    apply_attention_policy,
    build_judge_prompt,
    checkpoint_temporal_facts,
    filter_snapshot_attention_policy,
    run_llm_benchmark,
    snapshot_to_context_dict,
)
from personal_enigma.evaluation.metrics.support_fitness import (
    RescueRegressionOutcome,
    classify_arm_outcome,
    compute_rescue_regression_metrics,
)
from personal_enigma.reasoning import (
    PaygReasoningService,
    ReasoningMode,
    RecordingPaygTransport,
    ReplayPaygTransport,
)
from personal_enigma.reasoning.structured_output import (
    JUDGE_V1_SYSTEM_PROMPT,
    JudgeV1ParseError,
    ReasonCode,
    parse_judge_v1_output,
)

REPO = Path(__file__).resolve().parents[3]
GT = REPO / "scenarios" / "alex-v1" / "ground_truth"
BASELINES = Path(__file__).resolve().parents[1] / "fixtures" / "baselines" / "arm-a"
MINI_CPS = ["cp-2026-01-14T10:00", "cp-2026-01-21T13:30", "cp-2026-01-11T11:00"]


def test_parse_judge_v1_output_valid() -> None:
    out = parse_judge_v1_output(surface_expenses_json())
    assert out.next_action is not None
    assert out.next_action.title == "Gather receipts"
    assert out.attention.decision == "surface"


def test_parse_judge_v1_unknown_reason_code_maps_to_other() -> None:
    payload = json.loads(surface_expenses_json())
    payload["attention"]["reason_codes"] = ["MADE_UP_CODE"]
    out = parse_judge_v1_output(json.dumps(payload))
    assert out.attention.reason_codes == [ReasonCode.OTHER]


def test_parse_judge_v1_output_invalid() -> None:
    with pytest.raises(JudgeV1ParseError):
        parse_judge_v1_output("not json")


def test_apply_attention_policy_surface_threshold() -> None:
    from personal_enigma.reasoning.structured_output import JudgeV1Attention

    low_conf = JudgeV1Attention(
        decision="surface",
        priority=4,
        confidence=0.2,
        reason_codes=[ReasonCode.DEADLINE_APPROACHING],
        evidence_ids=["rem-expenses"],
    )
    policy = apply_attention_policy(low_conf)
    assert policy.decision == "suppress"
    assert policy.reason == "surface_threshold"


def test_filter_snapshot_attention_policy_skips_suppressed() -> None:
    from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot

    snap = load_checkpoint_snapshot(BASELINES / f"{MINI_CPS[0]}.json")
    suppressed = next(c for c in snap.candidate_set if c.suppressed)
    output = parse_judge_v1_output(surface_expenses_json())
    ranked = [(suppressed, output)]
    alerts = filter_snapshot_attention_policy(snap, ranked)
    assert alerts == []


def test_prompt_excludes_contract_markers() -> None:
    from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot

    snap = load_checkpoint_snapshot(BASELINES / f"{MINI_CPS[0]}.json")
    prompt = build_judge_prompt(snap, snap.candidate_set[0])
    for marker in FORBIDDEN_PROMPT_MARKERS:
        assert marker.lower() not in prompt.lower()


def test_judge_context_excludes_arm_a_surfaced_state() -> None:
    from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot

    snap = load_checkpoint_snapshot(BASELINES / f"{MINI_CPS[0]}.json")
    assert snap.alerts
    context = snapshot_to_context_dict(snap)
    assert "surfaced" not in context
    for candidate in context["candidates"]:
        assert "suppressed" not in candidate


def test_judge_context_includes_temporal_facts() -> None:
    from datetime import UTC, datetime

    at = datetime(2026, 1, 11, 11, 0, tzinfo=UTC)
    facts = checkpoint_temporal_facts(at)
    assert facts == {
        "now": "2026-01-11T11:00:00Z",
        "day_of_week": "Sunday",
        "is_weekend": True,
    }

    from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot

    snap = load_checkpoint_snapshot(BASELINES / "cp-2026-01-11T11:00.json")
    context = snapshot_to_context_dict(snap)
    assert context["now"] == "2026-01-11T11:00:00Z"
    assert context["day_of_week"] == "Sunday"
    assert context["is_weekend"] is True


def test_judge_prompt_surface_semantics() -> None:
    from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot

    snap = load_checkpoint_snapshot(BASELINES / f"{MINI_CPS[0]}.json")
    prompt = build_judge_prompt(snap, snap.candidate_set[0])
    lowered = prompt.lower()
    for phrase in (
        "warrants the user's attention **now**",
        "open obligation alone does not justify surface",
        "zero surfaces is ok",
        "evaluate evidence independently",
    ):
        assert phrase in lowered or phrase.replace("**", "") in lowered
    assert "on weekends" not in lowered
    assert "suppress work" not in lowered
    assert "warrants the user's attention now" in JUDGE_V1_SYSTEM_PROMPT.lower()
    assert "zero surfaced items" in JUDGE_V1_SYSTEM_PROMPT.lower()


def test_classify_rescue_regression() -> None:
    assert classify_arm_outcome(arm_a_pass=False, arm_b_pass=True) == (
        RescueRegressionOutcome.RESCUE
    )
    assert classify_arm_outcome(arm_a_pass=True, arm_b_pass=False) == (
        RescueRegressionOutcome.REGRESSION
    )


def test_record_and_replay_benchmark(tmp_path: Path) -> None:
    truth = load_evaluation_truth(GT)
    inner = PerCandidateJudgeMockTransport()
    recorder = RecordingPaygTransport(inner, scenario="gate-mini")
    service = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=recorder)

    from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
    from personal_enigma.evaluation.llm_benchmark import (
        score_arm_b,
        snapshot_to_transformed_context,
    )

    snap = load_checkpoint_snapshot(BASELINES / f"{MINI_CPS[0]}.json")
    result = score_arm_b(
        snap,
        truth,
        service=service,
        context=snapshot_to_transformed_context(snap),
        judge_arm="b1",
    )
    assert result.candidate_judgements
    assert any(
        j.output and j.output.attention.decision == "surface"
        for j in result.candidate_judgements
    )

    replay_path = tmp_path / "gate.json"
    recorder.save(replay_path)

    report = run_llm_benchmark(
        truth,
        baseline_dir=BASELINES,
        replay_fixture=replay_path,
        checkpoint_ids=MINI_CPS[:1],
        judge_arm="b1",
    )
    assert report.arm_a
    assert report.arm_b
    assert report.arm_b[0].candidate_judgements
    assert report.rescue_regression_counts

    rescue = compute_rescue_regression_metrics(
        checkpoint_id=MINI_CPS[0],
        arm_a=report.arm_a[0].metrics,
        arm_b=report.arm_b[0].metrics,
    )
    assert rescue

    replay = ReplayPaygTransport(replay_path, force_offline=True)
    client = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=replay)
    first = snap.candidate_set[0]
    assert client.reason(
        snapshot_to_transformed_context(snap),
        prompt=build_judge_prompt(snap, first),
        model="payg-gate",
    ).text


def test_attention_only_skips_next_action_scoring() -> None:
    from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
    from personal_enigma.evaluation.llm_benchmark import (
        score_arm_b,
        snapshot_to_transformed_context,
    )

    truth = load_evaluation_truth(GT)
    snap = load_checkpoint_snapshot(BASELINES / f"{MINI_CPS[0]}.json")
    service = PaygReasoningService(
        mode=ReasoningMode.ENABLED, transport=PerCandidateJudgeMockTransport()
    )
    result = score_arm_b(
        snap,
        truth,
        service=service,
        context=snapshot_to_transformed_context(snap),
        attention_only=True,
        judge_arm="b1",
    )
    assert result.metrics.next_action_checkpoints_scored == 0
    assert result.metrics.next_action_accuracy == 1.0
