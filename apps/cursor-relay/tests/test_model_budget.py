"""Regression tests: optional model passthrough and premium escalation gating."""

from __future__ import annotations

from tokens import APPROVER_CALLER, DISPATCHER_CALLER

from personal_enigma.cursor_relay.allowlist import DispatchTarget
from personal_enigma.cursor_relay.create_contract import build_create_payload
from personal_enigma.cursor_relay.cursor_client import MockCursorClient
from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.model_budget import (
    enforce_model_escalation_policy,
    extract_model_escalation_reason,
    is_premium_model,
)
from personal_enigma.cursor_relay.relay import RelayService

ENV_UUID = "1baeb513-9c77-11f1-ba66-0e7d0216e441"
VALID_REASON = "Architecture spike after default-model attempt stalled on cross-package design"


def _dispatch_params(**overrides: object) -> dict:
    base = {
        "idempotency_key": "model-budget-1",
        "repository": "oscarhilton/enigma-assistant-",
        "environment": ENV_UUID,
        "head_branch": "ticket/cloud-02-cursor-relay-mcp",
        "prompt": "routine infra work",
        "job_brief": {"authorization": {"dry_run": True}},
    }
    base.update(overrides)
    return base


def test_is_premium_model_classifies_observed_models() -> None:
    assert not is_premium_model("composer-2")
    assert is_premium_model("composer-2.5")
    assert is_premium_model("composer-2.5-fast")
    assert is_premium_model("cursor-grok-4.6-high-fast")
    assert is_premium_model("gpt-5.3-codex")


def test_extract_model_escalation_reason_from_params_and_brief() -> None:
    assert (
        extract_model_escalation_reason({"model_escalation_reason": "  spike needed  "})
        == "spike needed"
    )
    assert (
        extract_model_escalation_reason(
            {"job_brief": {"model_escalation_reason": "from brief top"}}
        )
        == "from brief top"
    )
    assert (
        extract_model_escalation_reason(
            {"job_brief": {"model_escalation": {"reason": "nested reason"}}}
        )
        == "nested reason"
    )
    assert extract_model_escalation_reason({}) is None


def test_enforce_model_escalation_policy_requires_reason_for_premium() -> None:
    import pytest

    from personal_enigma.cursor_relay.approval import ApprovalError

    with pytest.raises(ApprovalError) as exc:
        enforce_model_escalation_policy({}, model="composer-2.5-fast")
    assert exc.value.code == "model_escalation_reason_required"

    reason = enforce_model_escalation_policy(
        {"model_escalation_reason": VALID_REASON},
        model="composer-2.5-fast",
    )
    assert reason == VALID_REASON

    assert enforce_model_escalation_policy({}, model="composer-2") is None


def test_build_create_payload_omits_model_when_unset() -> None:
    target = DispatchTarget(
        repository="oscarhilton/enigma-assistant-",
        environment=ENV_UUID,
        head_branch="ticket/example",
        model=None,
    )
    payload = build_create_payload(prompt="hello", target=target)
    assert "model" not in payload


def test_build_create_payload_includes_explicit_composer_2_5() -> None:
    target = DispatchTarget(
        repository="oscarhilton/enigma-assistant-",
        environment=ENV_UUID,
        head_branch="ticket/example",
        model="composer-2.5",
    )
    payload = build_create_payload(prompt="architecture spike", target=target)
    assert payload["model"] == {"id": "composer-2.5"}


def test_dispatch_omitted_model_has_no_model_in_create_plan(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params(idempotency_key="omit-model-dispatch"),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    plan = result["observed_state"]["create_request_plan"]
    assert "model" not in plan
    assert result["observed_state"].get("model") is None
    assert "model_escalation_reason" not in result["observed_state"]


def test_dispatch_explicit_composer_2_5_requires_escalation_reason(
    service: RelayService,
) -> None:
    denied = service.invoke(
        "dispatch",
        _dispatch_params(
            idempotency_key="explicit-25-no-reason",
            model="composer-2.5",
        ),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(denied)
    assert "model_escalation_reason_required" in denied["recommended_action"]["rationale"]


def test_dispatch_explicit_composer_2_5_with_reason_in_create_plan(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params(
            idempotency_key="explicit-25-dispatch",
            model="composer-2.5",
            model_escalation_reason=VALID_REASON,
        ),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    plan = result["observed_state"]["create_request_plan"]
    assert plan["model"] == {"id": "composer-2.5"}
    assert result["observed_state"]["model"] == "composer-2.5"
    assert result["observed_state"]["model_escalation"] is True
    assert result["observed_state"]["model_escalation_reason"] == VALID_REASON


def test_request_review_omitted_model_has_no_model_in_create_plan(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "request_review",
        {
            "idempotency_key": "omit-model-review",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "ticket/cloud-02-cursor-relay-mcp",
            "job_brief": {"authorization": {"dry_run": True}},
        },
        caller=APPROVER_CALLER,
    )
    validate_handoff(result)
    plan = result["observed_state"]["create_request_plan"]
    assert "model" not in plan


def test_request_review_premium_model_requires_escalation_reason(
    service: RelayService,
) -> None:
    denied = service.invoke(
        "request_review",
        {
            "idempotency_key": "review-premium-no-reason",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "ticket/cloud-02-cursor-relay-mcp",
            "model": "composer-2.5-fast",
            "job_brief": {"authorization": {"dry_run": True}},
        },
        caller=APPROVER_CALLER,
    )
    validate_handoff(denied)
    assert "model_escalation_reason_required" in denied["recommended_action"]["rationale"]


def test_model_allowlist_denial_unchanged(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params(
            idempotency_key="bad-model",
            model="unapproved-model-xyz",
            model_escalation_reason=VALID_REASON,
            job_brief={"authorization": {"dry_run": True}},
        ),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert "allowlist_denied" in result["recommended_action"]["rationale"]
