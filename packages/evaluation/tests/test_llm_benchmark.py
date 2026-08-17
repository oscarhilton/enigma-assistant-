"""Tests for LLM judge benchmark (R03)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from personal_enigma.evaluation.evaluation_truth import load_evaluation_truth
from personal_enigma.evaluation.llm_benchmark import (
    FORBIDDEN_PROMPT_MARKERS,
    build_judge_prompt,
    run_llm_benchmark,
)
from personal_enigma.reasoning import (
    MockPaygTransport,
    PaygReasoningService,
    ReasoningMode,
    RecordingPaygTransport,
    ReplayPaygTransport,
)
from personal_enigma.reasoning.structured_output import LlmJudgeParseError, parse_llm_judge_output

REPO = Path(__file__).resolve().parents[3]
GT = REPO / "scenarios" / "alex-v1" / "ground_truth"
BASELINES = Path(__file__).resolve().parents[1] / "fixtures" / "baselines" / "arm-a"
MINI_CPS = ["cp-2026-01-14T10:00", "cp-2026-01-21T13:30", "cp-2026-01-11T11:00"]

_LLM_JSON = json.dumps(
    {
        "attention": {
            "item_id": "item-obligation_december_expenses",
            "behaviour": "surface",
            "priority": 4,
        },
        "next_action": {
            "title": "Gather receipts",
            "estimated_minutes": 5,
            "effort": "light",
            "why_this_now": "Expense deadline approaching",
        },
    }
)


def test_parse_llm_judge_output_valid() -> None:
    out = parse_llm_judge_output(_LLM_JSON)
    assert out.next_action.title == "Gather receipts"


def test_parse_llm_judge_output_invalid() -> None:
    with pytest.raises(LlmJudgeParseError):
        parse_llm_judge_output("not json")


def test_prompt_excludes_contract_markers() -> None:
    from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot

    snap = load_checkpoint_snapshot(BASELINES / f"{MINI_CPS[0]}.json")
    prompt = build_judge_prompt(snap)
    for marker in FORBIDDEN_PROMPT_MARKERS:
        assert marker.lower() not in prompt.lower()


def test_record_and_replay_benchmark(tmp_path: Path) -> None:
    truth = load_evaluation_truth(GT)
    inner = MockPaygTransport(response_text=_LLM_JSON)
    recorder = RecordingPaygTransport(inner, scenario="gate-mini")
    service = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=recorder)

    from personal_enigma.evaluation.checkpoint_runner import load_checkpoint_snapshot
    from personal_enigma.evaluation.llm_benchmark import (
        score_arm_b,
        snapshot_to_transformed_context,
    )

    snap = load_checkpoint_snapshot(BASELINES / f"{MINI_CPS[0]}.json")
    score_arm_b(
        snap,
        truth,
        service=service,
        context=snapshot_to_transformed_context(snap),
    )
    replay_path = tmp_path / "gate.json"
    recorder.save(replay_path)

    report = run_llm_benchmark(
        truth,
        baseline_dir=BASELINES,
        replay_fixture=replay_path,
        checkpoint_ids=MINI_CPS[:1],
    )
    assert report.arm_a
    assert report.arm_b
    assert report.arm_b[0].llm_output is not None

    replay = ReplayPaygTransport(replay_path, force_offline=True)
    client = PaygReasoningService(mode=ReasoningMode.ENABLED, transport=replay)
    assert client.reason(
        snapshot_to_transformed_context(snap),
        prompt=build_judge_prompt(snap),
        model="payg-gate",
    ).text == _LLM_JSON
