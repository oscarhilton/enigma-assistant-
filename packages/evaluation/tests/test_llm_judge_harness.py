"""Arm B LLM Judge harness — offline replay / authority / no live CI."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest
from pydantic import ValidationError

from personal_enigma.evaluation.llm_judge import (
    LIVE_ENV_FLAG,
    JudgeHarness,
    JudgeHarnessError,
    JudgeHarnessMode,
    JudgementAttention,
    JudgementImportance,
    JudgementKind,
    JudgementStatus,
    JudgementTiming,
    JudgeResponse,
    StructuredJudgement,
    apply_code_authority,
    default_fixture_path,
    live_enabled_from_env,
    load_judge_fixture,
)
from personal_enigma.reasoning.errors import ReasoningDisabledError
from personal_enigma.transformation import TransformedContext

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "llm_judge"


def test_default_fixture_loads_parents_brunch() -> None:
    path = default_fixture_path()
    assert path.name == "parents-brunch-wed-noon.json"
    request, response = load_judge_fixture(path)
    assert request.checkpoint_id == "alex-wed-21-jan-noon"
    assert "cand-brunch-parents" in request.candidate_id_set()
    assert len(response.judgements) == 3


def test_replay_harness_applies_authority() -> None:
    harness = JudgeHarness(mode=JudgeHarnessMode.REPLAY)
    result = harness.run()
    assert result.ok
    assert result.privacy_violations == 0
    assert result.schema_failures == 0
    by_id = {j.candidate_id: j for j in result.accepted}
    assert by_id["cand-brunch-parents"].attention is JudgementAttention.MUST_SURFACE
    assert by_id["cand-dentist"].attention is JudgementAttention.SUPPRESS


def test_invented_evidence_ids_rejected() -> None:
    request, _ = load_judge_fixture(default_fixture_path())
    bad = JudgeResponse(
        judgements=[
            StructuredJudgement(
                candidate_id="cand-brunch-parents",
                kind=JudgementKind.OBLIGATION,
                status=JudgementStatus.OPEN,
                importance=JudgementImportance.CRITICAL,
                attention=JudgementAttention.MUST_SURFACE,
                timing=JudgementTiming.SOON,
                confidence=0.9,
                reason_codes=["multi_source"],
                evidence_ids=["rem-brunch-book", "invented-ev-99"],
            )
        ]
    )
    result = apply_code_authority(request, bad)
    assert result.schema_failures == 1
    assert result.accepted == []
    assert "invented evidence_ids" in result.rejected[0][1]


def test_must_suppress_policy_clamps_attention() -> None:
    request, response = load_judge_fixture(default_fixture_path())
    # Model wrongly wants dentist surfaced; policy clamps.
    forced = response.model_copy(
        update={
            "judgements": [
                j.model_copy(update={"attention": JudgementAttention.MUST_SURFACE})
                if j.candidate_id == "cand-dentist"
                else j
                for j in response.judgements
            ]
        }
    )
    result = apply_code_authority(
        request,
        forced,
        must_suppress_ids={"cand-dentist"},
    )
    dentist = next(j for j in result.accepted if j.candidate_id == "cand-dentist")
    assert dentist.attention is JudgementAttention.SUPPRESS


def test_dry_run_never_opens_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbid(*_a: object, **_k: object) -> None:
        raise AssertionError("network must not open in DRY_RUN")

    monkeypatch.setattr(socket.socket, "connect", forbid)
    monkeypatch.setattr(socket, "create_connection", forbid)

    request, _ = load_judge_fixture(default_fixture_path())
    result = JudgeHarness(mode=JudgeHarnessMode.DRY_RUN).run(request)
    assert result.ok
    assert result.accepted == []


def test_disabled_raises() -> None:
    with pytest.raises(ReasoningDisabledError):
        JudgeHarness(mode=JudgeHarnessMode.DISABLED).run()


def test_live_requires_env_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(LIVE_ENV_FLAG, raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert live_enabled_from_env(environ={}) is False
    request, _ = load_judge_fixture(default_fixture_path())
    with pytest.raises(JudgeHarnessError, match="ENIGMA_LLM_JUDGE_LIVE"):
        JudgeHarness(mode=JudgeHarnessMode.ENABLED).run(request)


def test_reason_codes_reject_prose() -> None:
    with pytest.raises(ValidationError):
        StructuredJudgement(
            candidate_id="c1",
            kind=JudgementKind.NOISE,
            status=JudgementStatus.OPEN,
            importance=JudgementImportance.NONE,
            attention=JudgementAttention.SUPPRESS,
            timing=JudgementTiming.NA,
            confidence=0.5,
            reason_codes=["this is chain of thought"],
            evidence_ids=[],
        )


def test_unsafe_context_counts_privacy_violation() -> None:
    request, response = load_judge_fixture(default_fixture_path())
    unsafe = request.model_copy(
        update={
            "context": TransformedContext(
                summary="leak PrivatePerson raw",
                entities=[],
                metadata={},
                may_transmit_remotely=True,
            )
        }
    )
    result = apply_code_authority(unsafe, response)
    assert result.privacy_violations == 1
    assert result.accepted == []


def test_fixture_json_has_catalogue_todo() -> None:
    data = json.loads((FIXTURES / "parents-brunch-wed-noon.json").read_text(encoding="utf-8"))
    assert "F-judgement-scenario-catalogue" in data["notes"]["truth_todo"]
