"""Regression: omitted dry_run must not silently become a successful dry-run."""

from __future__ import annotations

from typing import Any

from tokens import APPROVER_CALLER, DISPATCHER_CALLER, READER_CALLER

from personal_enigma.cursor_relay.allowlist import DispatchTarget
from personal_enigma.cursor_relay.approval import parse_job_brief_auth
from personal_enigma.cursor_relay.create_contract import build_create_payload
from personal_enigma.cursor_relay.cursor_client import MockCursorClient
from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.relay import RelayService

ENV_UUID = "1baeb513-9c77-11f1-ba66-0e7d0216e441"
HEAD = "ticket/relay-dry-run-default-contract"


def _dispatch_params(key: str, job_brief: dict[str, Any] | None) -> dict[str, Any]:
    params: dict[str, Any] = {
        "idempotency_key": key,
        "repository": "oscarhilton/enigma-assistant-",
        "environment": ENV_UUID,
        "head_branch": HEAD,
        "prompt": "contract probe",
    }
    if job_brief is not None:
        params["job_brief"] = job_brief
    return params


def _review_params(key: str, job_brief: dict[str, Any] | None) -> dict[str, Any]:
    params: dict[str, Any] = {
        "idempotency_key": key,
        "repository": "oscarhilton/enigma-assistant-",
        "environment": ENV_UUID,
        "head_branch": "cursor/review-dry-run-default",
        "prompt": "review contract probe",
    }
    if job_brief is not None:
        params["job_brief"] = job_brief
    return params


LIVE_AUTH = {"authorization": {"dry_run": False, "allow_push": True}}
DRY_AUTH = {"authorization": {"dry_run": True}}
OMITTED_WITH_AUTH = {"authorization": {"allow_push": True, "allow_open_pr": True}}
OMITTED_WITHOUT_AUTH = {"authorization": {"allow_merge": False}}


def test_parse_omitted_dry_run_is_none_not_true() -> None:
    assert parse_job_brief_auth(None).dry_run is None
    assert parse_job_brief_auth({}).dry_run is None
    assert parse_job_brief_auth({"authorization": {}}).dry_run is None
    assert parse_job_brief_auth(OMITTED_WITH_AUTH).dry_run is None
    assert parse_job_brief_auth(DRY_AUTH).dry_run is True
    assert parse_job_brief_auth(LIVE_AUTH).dry_run is False


def test_create_payload_omitted_dry_run_does_not_claim_true() -> None:
    payload = build_create_payload(
        prompt="hello",
        target=DispatchTarget(
            repository="oscarhilton/enigma-assistant-",
            environment=ENV_UUID,
            head_branch=HEAD,
            base_branch="main",
        ),
        job_brief=OMITTED_WITH_AUTH,
    )
    text = payload["prompt"]["text"]
    assert "dry_run=True" not in text
    assert "dry_run=False" in text


def test_dispatch_explicit_dry_run_does_not_post(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("dry-explicit", DRY_AUTH),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    observed = result["observed_state"]
    assert observed["dry_run"] is True
    assert observed["mutating"] is False
    assert observed.get("agent_id") is None


def test_dispatch_explicit_live_without_write_flags_still_posts(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    """Explicit dry_run=false remains live subject to role authorization."""

    result = service.invoke(
        "dispatch",
        _dispatch_params("live-explicit-no-flags", {"authorization": {"dry_run": False}}),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert len(mock_cursor.create_calls) == 1
    assert result["observed_state"]["dry_run"] is False
    assert result["observed_state"]["agent_id"]


def test_dispatch_explicit_live_posts(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("live-explicit", LIVE_AUTH),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert len(mock_cursor.create_calls) == 1
    observed = result["observed_state"]
    assert observed["dry_run"] is False
    assert observed["mutating"] is True
    assert observed["agent_id"]


def test_dispatch_omitted_dry_run_with_sufficient_auth_posts(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("omit-auth", OMITTED_WITH_AUTH),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert len(mock_cursor.create_calls) == 1
    observed = result["observed_state"]
    assert observed["dry_run"] is False
    assert observed["mutating"] is True
    assert observed["agent_id"]
    prompt_text = mock_cursor.create_calls[0]["prompt"]["text"]
    assert "dry_run=True" not in prompt_text


def test_dispatch_omitted_dry_run_without_sufficient_auth_fails_not_dry_run(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("omit-no-auth", OMITTED_WITHOUT_AUTH),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    assert result["recommended_action"]["kind"] == "stop_needs_human"
    assert "live_not_authorized" in result["recommended_action"]["rationale"]
    assert result["observed_state"].get("dry_run") is not True
    assert result["observed_state"].get("agent_id") is None


def test_dispatch_omitted_dry_run_wrong_role_fails_not_dry_run(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("omit-reader", OMITTED_WITH_AUTH),
        caller=READER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    assert "approval_denied" in result["recommended_action"]["rationale"]
    assert result["observed_state"].get("dry_run") is not True


def test_request_review_explicit_dry_run_does_not_post(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "request_review",
        _review_params("rr-dry-explicit", DRY_AUTH),
        caller=APPROVER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    assert result["observed_state"]["dry_run"] is True
    assert result["observed_state"].get("agent_id") is None


def test_request_review_explicit_live_posts(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "request_review",
        _review_params("rr-live-explicit", LIVE_AUTH),
        caller=APPROVER_CALLER,
    )
    validate_handoff(result)
    assert len(mock_cursor.create_calls) == 1
    assert result["observed_state"]["dry_run"] is False
    assert result["observed_state"]["agent_id"]
    assert result["observed_state"].get("merge") is False


def test_request_review_omitted_dry_run_with_sufficient_auth_posts(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "request_review",
        _review_params("rr-omit-auth", OMITTED_WITH_AUTH),
        caller=APPROVER_CALLER,
    )
    validate_handoff(result)
    assert len(mock_cursor.create_calls) == 1
    assert result["observed_state"]["dry_run"] is False
    assert result["observed_state"]["agent_id"]
    prompt_text = mock_cursor.create_calls[0]["prompt"]["text"]
    assert "dry_run=True" not in prompt_text


def test_request_review_omitted_dry_run_without_sufficient_auth_fails_not_dry_run(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "request_review",
        _review_params("rr-omit-no-auth", OMITTED_WITHOUT_AUTH),
        caller=APPROVER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    assert result["recommended_action"]["kind"] == "stop_needs_human"
    assert "live_not_authorized" in result["recommended_action"]["rationale"]
    assert result["observed_state"].get("dry_run") is not True
    assert result["observed_state"].get("agent_id") is None


def test_request_review_omitted_dry_run_wrong_role_fails_not_dry_run(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    result = service.invoke(
        "request_review",
        _review_params("rr-omit-dispatcher", OMITTED_WITH_AUTH),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert mock_cursor.create_calls == []
    assert "approval_denied" in result["recommended_action"]["rationale"]
    assert result["observed_state"].get("dry_run") is not True
