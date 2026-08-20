"""Contract tests for Cursor create-agent payload and dry-run semantics."""

from __future__ import annotations

import json

import httpx
from tokens import APPROVER_CALLER, DISPATCHER_CALLER

from personal_enigma.cursor_relay.allowlist import DispatchTarget
from personal_enigma.cursor_relay.create_contract import (
    CANONICAL_ENV_NAME,
    PENDING_BRANCH,
    build_create_payload,
    canonicalize_environment_name,
    extract_validation_fields,
    redact_create_payload,
)
from personal_enigma.cursor_relay.cursor_client import MockCursorClient, _safe_http_error
from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.relay import RelayService

ENV_UUID = "1baeb513-9c77-11f1-ba66-0e7d0216e441"


def _target(*, environment: str = ENV_UUID) -> DispatchTarget:
    return DispatchTarget(
        repository="oscarhilton/enigma-assistant-",
        environment=environment,
        head_branch="ticket/kernel-01-turn-kernel",
        model="composer-2",
        base_branch="main",
    )


def test_canonicalize_uuid_to_env_name() -> None:
    assert canonicalize_environment_name(ENV_UUID) == CANONICAL_ENV_NAME
    assert canonicalize_environment_name(CANONICAL_ENV_NAME) == CANONICAL_ENV_NAME


def test_exact_create_request_body_for_named_env() -> None:
    payload = build_create_payload(
        prompt="hello",
        target=_target(environment=ENV_UUID),
        name="relay:test",
        auto_create_pr=False,
        job_brief={"authorization": {"dry_run": False, "allow_push": True}},
    )
    assert payload["env"] == {"type": "cloud", "name": "enigma-assistant-"}
    assert "repos" not in payload
    assert "workOnCurrentBranch" not in payload
    assert payload["autoCreatePR"] is False
    assert payload["model"] == {"id": "composer-2"}
    assert payload["name"] == "relay:test"
    assert "prompt" in payload and "text" in payload["prompt"]
    # UUID must not appear as env.name
    assert payload["env"]["name"] != ENV_UUID
    assert ENV_UUID not in payload["env"]["name"]


def test_named_env_from_display_name_also_omits_repos() -> None:
    payload = build_create_payload(
        prompt="x",
        target=_target(environment="enigma-assistant-"),
    )
    assert payload["env"]["name"] == "enigma-assistant-"
    assert "repos" not in payload
    assert "workOnCurrentBranch" not in payload


def test_dry_run_does_not_post_agents(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        {
            "idempotency_key": "dry-1",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "ticket/cloud-03-create-contract",
            "prompt": "plan only",
            "job_brief": {"authorization": {"dry_run": True}},
        },
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    observed = result["observed_state"]
    assert observed["dry_run"] is True
    assert observed["mutating"] is False
    assert observed.get("agent_id") is None
    assert observed["branch"] == PENDING_BRANCH
    assert observed["requested_head_branch"] == "ticket/cloud-03-create-contract"
    assert observed["actual_head_branch"] is None
    plan = observed["create_request_plan"]
    assert plan["env"]["name"] == "enigma-assistant-"
    assert "repos" not in plan
    assert "workOnCurrentBranch" not in plan
    assert "text" not in plan.get("prompt", {})  # redacted to preview/hash only


def test_mutating_dispatch_still_pending_branch_until_status(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    dispatched = service.invoke(
        "dispatch",
        {
            "idempotency_key": "mut-1",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "ticket/cloud-03-create-contract",
            "base_branch": "main",
            "prompt": "go",
            "job_brief": {
                "authorization": {"dry_run": False, "allow_push": True}
            },
        },
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(dispatched)
    assert len(mock_cursor.create_calls) == 1
    body = mock_cursor.create_calls[0]
    assert body["env"]["name"] == "enigma-assistant-"
    assert "repos" not in body
    assert "workOnCurrentBranch" not in body
    assert dispatched["observed_state"]["branch"] == PENDING_BRANCH
    assert dispatched["observed_state"]["requested_head_branch"] == (
        "ticket/cloud-03-create-contract"
    )
    assert dispatched["observed_state"]["actual_head_branch"] is None

    agent_id = dispatched["observed_state"]["agent_id"]
    run_id = dispatched["observed_state"]["run_id"]
    status = service.invoke(
        "status",
        {
            "agent_id": agent_id,
            "run_id": run_id,
            "head_branch": "ticket/cloud-03-create-contract",
        },
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(status)
    assert status["observed_state"]["actual_head_branch"] == "cursor/auto-0001"
    assert status["observed_state"]["branch"] == "cursor/auto-0001"
    assert status["observed_state"]["requested_head_branch"] == (
        "ticket/cloud-03-create-contract"
    )


def test_redacted_http_400_validation_only_allowlisted_fields() -> None:
    request = httpx.Request("POST", "https://api.cursor.com/v1/agents")
    response = httpx.Response(
        400,
        request=request,
        headers={"Authorization": "Bearer super-secret", "X-Leak": "nope"},
        json={
            "error": {
                "code": "invalid_argument",
                "message": "env.name must be a bound environment name",
                "field": "env.name",
                "request_id": "should-not-surface",
                "debug": {"stack": "secret-stack"},
            },
            "raw_request": {"api_key": "sk-leak"},
        },
    )
    err = httpx.HTTPStatusError("bad", request=request, response=response)
    safe = _safe_http_error(err)
    assert safe.code == "cursor_validation_error"
    assert "Authorization" not in str(safe)
    assert "super-secret" not in str(safe)
    assert "sk-leak" not in str(safe)
    assert "secret-stack" not in str(safe)
    assert "request_id" not in str(safe)
    assert all(set(item) <= {"code", "message", "field"} for item in safe.validation)
    assert any(item.get("field") == "env.name" for item in safe.validation)


def test_dispatch_surfaces_redacted_validation(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    mock_cursor.fail_next = "http_400"
    mock_cursor.fail_validation = [
        {"code": "invalid_argument", "message": "bad", "field": "env.name"}
    ]
    result = service.invoke(
        "dispatch",
        {
            "idempotency_key": "val-1",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": "enigma-assistant-",
            "head_branch": "ticket/cloud-03-create-contract",
            "prompt": "x",
            "job_brief": {"authorization": {"dry_run": False, "allow_push": True}},
        },
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert "cursor_validation_error" in result["recommended_action"]["rationale"]
    observed = result["observed_state"]
    assert observed.get("cursor_validation")
    blob = json.dumps(result)
    assert "Authorization" not in blob
    assert "api_key" not in blob.lower() or "chatgpt_api_key" not in blob


def test_extract_validation_fields_truncates() -> None:
    long_msg = "x" * 500
    fields = extract_validation_fields({"code": "e", "message": long_msg, "field": "f"})
    assert fields
    assert len(fields[0]["message"]) <= 200
    assert fields[0]["message"].endswith("...")


def test_redact_create_payload_strips_prompt_text() -> None:
    payload = build_create_payload(prompt="secret sauce", target=_target())
    redacted = redact_create_payload(payload)
    assert "text" not in redacted["prompt"]
    assert redacted["prompt"]["text_chars"] == len(payload["prompt"]["text"])
    assert "secret sauce" not in json.dumps(redacted)


def test_request_review_dry_run_no_create(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "request_review",
        {
            "idempotency_key": "rr-dry",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": ENV_UUID,
            "head_branch": "cursor/review-cloud-03",
            "prompt": "review",
            "job_brief": {"authorization": {"dry_run": True}},
        },
        caller=APPROVER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    assert result["observed_state"]["dry_run"] is True
