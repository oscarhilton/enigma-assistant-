"""Regression: omitted model must pass through to Cursor without relay substitution."""

from __future__ import annotations

from tokens import APPROVER_CALLER, DISPATCHER_CALLER

from personal_enigma.cursor_relay.allowlist import DispatchTarget
from personal_enigma.cursor_relay.create_contract import build_create_payload, redact_create_payload
from personal_enigma.cursor_relay.cursor_client import MockCursorClient
from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.relay import RelayService

ENV_UUID = "1baeb513-9c77-11f1-ba66-0e7d0216e441"


def _dispatch_params(key: str, **overrides: object) -> dict:
    base = {
        "idempotency_key": key,
        "repository": "oscarhilton/enigma-assistant-",
        "environment": ENV_UUID,
        "head_branch": "ticket/relay-default-model-pass-through",
        "prompt": "hello",
        "job_brief": {"authorization": {"dry_run": False, "allow_push": True}},
    }
    base.update(overrides)
    return base


def test_build_create_payload_omits_model_when_unset() -> None:
    target = DispatchTarget(
        repository="oscarhilton/enigma-assistant-",
        environment=ENV_UUID,
        head_branch="ticket/relay-default-model-pass-through",
        base_branch="main",
    )
    payload = build_create_payload(prompt="hello", target=target)
    assert "model" not in payload


def test_build_create_payload_preserves_explicit_model() -> None:
    target = DispatchTarget(
        repository="oscarhilton/enigma-assistant-",
        environment=ENV_UUID,
        head_branch="ticket/relay-default-model-pass-through",
        model="composer-2.5",
        base_branch="main",
    )
    payload = build_create_payload(prompt="hello", target=target)
    assert payload["model"] == {"id": "composer-2.5"}


def test_dispatch_omitted_model_not_in_cursor_create_request(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("omit-model-1"),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert len(mock_cursor.create_calls) == 1
    body = mock_cursor.create_calls[0]
    assert "model" not in body
    observed = result["observed_state"]
    assert observed.get("model_source") == "omitted"
    assert "model" not in observed


def test_dispatch_explicit_composer_25_preserved(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("explicit-model-1", model="composer-2.5"),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls[-1]["model"] == {"id": "composer-2.5"}
    assert result["observed_state"]["model"] == "composer-2.5"
    assert "model_source" not in result["observed_state"]


def test_dispatch_invalid_explicit_model_rejected(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("bad-model-1", model="unapproved-model-xyz"),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert "allowlist_denied" in result["recommended_action"]["rationale"]
    assert mock_cursor.create_calls == []


def test_dry_run_omitted_model_plan_has_no_composer_2(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        {
            "idempotency_key": "dry-omit-model",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "ticket/relay-default-model-pass-through",
            "prompt": "plan only",
            "job_brief": {"authorization": {"dry_run": True}},
        },
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    observed = result["observed_state"]
    plan = observed["create_request_plan"]
    assert "model" not in plan
    assert "composer-2" not in str(plan)
    assert observed.get("model_source") == "omitted"


def test_request_review_omitted_model_not_in_cursor_create_request(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "request_review",
        {
            "idempotency_key": "rr-omit-model",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "cursor/review-omit-model",
            "prompt": "review",
            "job_brief": {"authorization": {"dry_run": False, "allow_push": True}},
        },
        caller=APPROVER_CALLER,
    )
    validate_handoff(result)
    assert len(mock_cursor.create_calls) == 1
    assert "model" not in mock_cursor.create_calls[0]
    plan = redact_create_payload(mock_cursor.create_calls[0])
    assert "model" not in plan


def test_request_review_dry_run_omitted_model_plan_has_no_model(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "request_review",
        {
            "idempotency_key": "rr-dry-omit",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "cursor/review-dry-omit",
            "prompt": "review",
            "job_brief": {"authorization": {"dry_run": True}},
        },
        caller=APPROVER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    plan = result["observed_state"]["create_request_plan"]
    assert "model" not in plan
    assert "composer-2" not in str(plan)
