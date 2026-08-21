"""Regression tests: optional model passthrough (Cursor default/green vs explicit escalation)."""

from __future__ import annotations

from tokens import APPROVER_CALLER, DISPATCHER_CALLER

from personal_enigma.cursor_relay.allowlist import DispatchTarget
from personal_enigma.cursor_relay.create_contract import build_create_payload
from personal_enigma.cursor_relay.cursor_client import MockCursorClient
from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.relay import RelayService

ENV_UUID = "1baeb513-9c77-11f1-ba66-0e7d0216e441"


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


def test_dispatch_explicit_composer_2_5_in_create_plan(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params(
            idempotency_key="explicit-25-dispatch",
            model="composer-2.5",
        ),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    plan = result["observed_state"]["create_request_plan"]
    assert plan["model"] == {"id": "composer-2.5"}
    assert result["observed_state"]["model"] == "composer-2.5"


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


def test_model_allowlist_denial_unchanged(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params(
            idempotency_key="bad-model",
            model="unapproved-model-xyz",
            job_brief={"authorization": {"dry_run": True}},
        ),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert "allowlist_denied" in result["recommended_action"]["rationale"]
