"""Tests for live benchmark budget ledger (R-L03)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from personal_enigma.evaluation.benchmark_budget import (
    HARD_CAP_USD,
    BenchmarkBudgetLedger,
    BudgetCapExceededError,
    BudgetGatedFireworksTransport,
    estimate_cost_usd,
)
from personal_enigma.reasoning.fireworks_transport import FireworksChatTransport
from personal_enigma.transformation import TransformedContext


def test_estimate_cost_usd_pricing_constants() -> None:
    # 100k input @ $0.15/M + 50k output @ $0.60/M = 0.015 + 0.03 = 0.045
    assert estimate_cost_usd(input_tokens=100_000, output_tokens=50_000) == pytest.approx(
        0.045
    )


def test_budget_refuses_projected_over_cap() -> None:
    ledger = BenchmarkBudgetLedger(cumulative_usd=0.79)
    # Pessimistic next call: $0.08 projected (400k in + ~33k max out)
    projected = ledger.projected_cost_usd(input_tokens=400_000, max_output_tokens=33_333)
    assert projected == pytest.approx(0.08, rel=1e-3)
    with pytest.raises(BudgetCapExceededError):
        ledger.check_can_spend(input_tokens=400_000, max_output_tokens=33_333)


def test_budget_allows_call_under_cap() -> None:
    ledger = BenchmarkBudgetLedger(cumulative_usd=0.79)
    projected = ledger.check_can_spend(input_tokens=10_000, max_output_tokens=512)
    assert projected < HARD_CAP_USD - 0.79


def test_audit_log_writes_jsonl(tmp_path: Any) -> None:
    ledger = BenchmarkBudgetLedger(
        audit_dir=tmp_path,
        cumulative_usd=0.0,
    )
    record = ledger.record_request(
        checkpoint_id="cp-2026-01-21T13:30",
        rep=1,
        prompt_tokens=800,
        completion_tokens=120,
        phase="smoke",
        model="accounts/fireworks/models/gpt-oss-120b",
    )
    assert record.cumulative_total_usd == pytest.approx(
        estimate_cost_usd(input_tokens=800, output_tokens=120)
    )
    lines = ledger.audit_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["checkpoint_id"] == "cp-2026-01-21T13:30"
    assert payload["rep"] == 1
    assert payload["prompt_tokens"] == 800
    assert payload["completion_tokens"] == 120
    assert "estimated_cost_usd" in payload
    assert "cumulative_total_usd" in payload
    assert "api_key" not in json.dumps(payload).lower()


def test_budget_gated_transport_records_and_refuses(tmp_path: Any) -> None:
    response = json.dumps(
        {
            "choices": [{"message": {"content": '{"ok": true}'}}],
            "usage": {"prompt_tokens": 500, "completion_tokens": 50},
        }
    ).encode("utf-8")

    class _FakeResponse:
        def read(self) -> bytes:
            return response

        def __enter__(self) -> _FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def _urlopen(_req: Any, timeout: float = 0) -> _FakeResponse:
        return _FakeResponse()

    inner = FireworksChatTransport(api_key="test-key", urlopen=_urlopen)
    ledger = BenchmarkBudgetLedger(audit_dir=tmp_path, cumulative_usd=0.0)
    transport = BudgetGatedFireworksTransport(transport=inner, ledger=ledger, phase="smoke")

    ctx = TransformedContext(
        summary="short prompt",
        entities=["A"],
        metadata={"checkpoint_id": "cp-smoke"},
        may_transmit_remotely=True,
    )
    result = transport.complete(prompt="judge", context=ctx, rep=0)
    assert result.usage is not None
    assert result.usage.estimated_cost_usd is not None
    assert ledger.cumulative_usd > 0
    assert ledger.audit_path.exists()

    ledger.cumulative_usd = 0.79
    with pytest.raises(BudgetCapExceededError):
        transport.complete(
            prompt="judge again",
            context=ctx,
            rep=1,
            budget_input_tokens=400_000,
            max_output_tokens=33_333,
        )


def test_budget_gated_transport_records_length_retry_both_attempts(tmp_path: Any) -> None:
    """Both initial and length-retry HTTP calls must count against HARD_CAP_USD."""
    truncated = json.dumps({"title": "Open expense spreadsheet", "estimated_minutes": 5})
    full = json.dumps(
        {
            "schema_version": "semantic-judge-v1",
            "obligation_strength": 0.96,
            "user_responsibility": 0.98,
            "importance": 0.82,
            "time_sensitivity": 0.88,
            "actionability_now": 0.91,
            "confidence": 0.95,
            "reason_codes": ["EXPLICIT_REQUEST"],
        }
    )
    calls = 0

    def _urlopen(_req: Any, timeout: float = 0) -> Any:
        nonlocal calls
        calls += 1
        if calls == 1:
            payload = json.dumps(
                {
                    "choices": [
                        {
                            "message": {"content": truncated},
                            "finish_reason": "length",
                        }
                    ],
                    "usage": {"prompt_tokens": 500, "completion_tokens": 512},
                }
            ).encode("utf-8")
        else:
            payload = json.dumps(
                {
                    "choices": [
                        {
                            "message": {"content": full},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 500, "completion_tokens": 800},
                }
            ).encode("utf-8")

        class _FakeResponse:
            def read(self) -> bytes:
                return payload

            def __enter__(self) -> _FakeResponse:
                return self

            def __exit__(self, *_args: object) -> None:
                return None

        return _FakeResponse()

    inner = FireworksChatTransport(api_key="test-key", urlopen=_urlopen)
    ledger = BenchmarkBudgetLedger(audit_dir=tmp_path, cumulative_usd=0.0)
    transport = BudgetGatedFireworksTransport(transport=inner, ledger=ledger, phase="smoke")
    ctx = TransformedContext(
        summary="short prompt",
        entities=["A"],
        metadata={"checkpoint_id": "cp-smoke", "judge_arm": "b2"},
        may_transmit_remotely=True,
    )
    result = transport.complete(prompt="judge", context=ctx, rep=0)
    assert result.metadata.get("retried_for_length") == "true"
    assert calls == 2
    assert len(ledger.records) == 2
    expected = estimate_cost_usd(input_tokens=500, output_tokens=512) + estimate_cost_usd(
        input_tokens=500, output_tokens=800
    )
    assert ledger.cumulative_usd == pytest.approx(expected)
    assert ledger.records[0].metadata.get("attempt") == "initial"
    assert ledger.records[1].metadata.get("attempt") == "length_retry"


def test_budget_gated_transport_refuses_length_retry_over_cap(tmp_path: Any) -> None:
    truncated = json.dumps({"title": "partial"})
    calls = 0

    def _urlopen(_req: Any, timeout: float = 0) -> Any:
        nonlocal calls
        calls += 1
        payload = json.dumps(
            {
                "choices": [
                    {
                        "message": {"content": truncated},
                        "finish_reason": "length",
                    }
                ],
                "usage": {"prompt_tokens": 500, "completion_tokens": 512},
            }
        ).encode("utf-8")

        class _FakeResponse:
            def read(self) -> bytes:
                return payload

            def __enter__(self) -> _FakeResponse:
                return self

            def __exit__(self, *_args: object) -> None:
                return None

        return _FakeResponse()

    inner = FireworksChatTransport(api_key="test-key", urlopen=_urlopen)
    ledger = BenchmarkBudgetLedger(audit_dir=tmp_path, cumulative_usd=0.799)
    transport = BudgetGatedFireworksTransport(transport=inner, ledger=ledger, phase="smoke")
    ctx = TransformedContext(
        summary="short prompt",
        entities=["A"],
        metadata={"checkpoint_id": "cp-smoke", "judge_arm": "b2"},
        may_transmit_remotely=True,
    )
    with pytest.raises(BudgetCapExceededError):
        transport.complete(prompt="judge", context=ctx, rep=0)
    assert calls == 1
    assert len(ledger.records) == 1
