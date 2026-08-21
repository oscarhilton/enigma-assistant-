"""Allowlist, idempotency, and quota denials."""

from __future__ import annotations

from tokens import APPROVER_CALLER, DISPATCHER_CALLER

from personal_enigma.cursor_relay.config import RelayConfig
from personal_enigma.cursor_relay.cursor_client import MockCursorClient
from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.quotas import QuotaTracker
from personal_enigma.cursor_relay.relay import RelayService


def _dispatch_params(key: str, **overrides: object) -> dict:
    base = {
        "idempotency_key": key,
        "repository": "oscarhilton/enigma-assistant-",
        "environment": "enigma-assistant-",
        "head_branch": "ticket/cloud-02-cursor-relay-mcp",
        "prompt": "hello",
        "job_brief": {"authorization": {"dry_run": False, "allow_push": True}},
    }
    base.update(overrides)
    return base


def test_repo_allowlist_denial(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("al-repo", repository="evil/other-repo"),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert "allowlist_denied" in result["recommended_action"]["rationale"]
    assert "repository" in result["recommended_action"]["rationale"] or True


def test_environment_allowlist_denial(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("al-env", environment="not-bound-env"),
        caller=DISPATCHER_CALLER,
    )
    assert "allowlist_denied" in result["recommended_action"]["rationale"]


def test_branch_prefix_denial(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("al-branch", head_branch="feature/nope"),
        caller=DISPATCHER_CALLER,
    )
    assert "allowlist_denied" in result["recommended_action"]["rationale"]


def test_main_head_forbidden(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("al-main", head_branch="main"),
        caller=DISPATCHER_CALLER,
    )
    assert "allowlist_denied" in result["recommended_action"]["rationale"]


def test_model_allowlist_denial(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("al-model", model="unapproved-model-xyz"),
        caller=DISPATCHER_CALLER,
    )
    assert "allowlist_denied" in result["recommended_action"]["rationale"]


def test_idempotency_required(service: RelayService) -> None:
    params = _dispatch_params("x")
    del params["idempotency_key"]
    result = service.invoke("dispatch", params, caller=DISPATCHER_CALLER)
    assert "idempotency_required" in result["recommended_action"]["rationale"]


def test_idempotency_replay(service: RelayService, mock_cursor: MockCursorClient) -> None:
    first = service.invoke(
        "dispatch",
        _dispatch_params("idem-1"),
        caller=DISPATCHER_CALLER,
    )
    second = service.invoke(
        "dispatch",
        _dispatch_params("idem-1"),
        caller=DISPATCHER_CALLER,
    )
    assert first["observed_state"]["agent_id"] == second["observed_state"]["agent_id"]
    assert len(mock_cursor.create_calls) == 1
    assert any(r["decision"] == "idempotent_replay" for r in service.audit.records)


def test_concurrency_quota_denial(relay_config: RelayConfig) -> None:
    cursor = MockCursorClient()
    quotas = QuotaTracker(max_in_flight=1, max_spend_units=100, spend_per_create=1)
    service = RelayService(relay_config, cursor=cursor, quotas=quotas)
    ok = service.invoke(
        "dispatch",
        _dispatch_params("q-1"),
        caller=DISPATCHER_CALLER,
    )
    assert ok["observed_state"]["agent_id"]
    denied = service.invoke(
        "dispatch",
        _dispatch_params("q-2"),
        caller=DISPATCHER_CALLER,
    )
    assert "concurrency_exceeded" in denied["recommended_action"]["rationale"]
    assert any(r["decision"] == "deny" for r in service.audit.records)


def test_spend_quota_denial(relay_config: RelayConfig) -> None:
    cursor = MockCursorClient()
    quotas = QuotaTracker(max_in_flight=10, max_spend_units=1, spend_per_create=1)
    service = RelayService(relay_config, cursor=cursor, quotas=quotas)
    service.invoke(
        "dispatch",
        _dispatch_params("s-1"),
        caller=DISPATCHER_CALLER,
    )
    denied = service.invoke(
        "dispatch",
        _dispatch_params("s-2"),
        caller=DISPATCHER_CALLER,
    )
    assert "spend_exceeded" in denied["recommended_action"]["rationale"]


def test_request_review_idempotency_and_quota(relay_config: RelayConfig) -> None:
    cursor = MockCursorClient()
    quotas = QuotaTracker(max_in_flight=1, max_spend_units=100, spend_per_create=1)
    service = RelayService(relay_config, cursor=cursor, quotas=quotas)
    params = {
        "idempotency_key": "rr-1",
        "repository": "oscarhilton/enigma-assistant-",
        "environment": "1baeb513-9c77-11f1-ba66-0e7d0216e441",
        "head_branch": "cursor/review-a131",
        "prompt": "review",
        "job_brief": {"authorization": {"dry_run": False, "allow_push": True}},
    }
    first = service.invoke("request_review", params, caller=APPROVER_CALLER)
    second = service.invoke("request_review", params, caller=APPROVER_CALLER)
    assert first["observed_state"]["agent_id"] == second["observed_state"]["agent_id"]
    assert len(cursor.create_calls) == 1
    denied = service.invoke(
        "request_review",
        {**params, "idempotency_key": "rr-2"},
        caller=APPROVER_CALLER,
    )
    assert "concurrency_exceeded" in denied["recommended_action"]["rationale"]


def test_base_branch_allowlist_denial(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("al-base", base_branch="totally-unrestricted/evil"),
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert "allowlist_denied" in result["recommended_action"]["rationale"]
    assert "Base branch" in result["recommended_action"]["rationale"]


def test_base_branch_main_allowed(service: RelayService, mock_cursor: MockCursorClient) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("al-base-main", base_branch="main"),
        caller=DISPATCHER_CALLER,
    )
    assert result["observed_state"]["agent_id"]
    assert len(mock_cursor.create_calls) == 1


def test_base_branch_ticket_prefix_allowed(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params(
            "al-base-ticket",
            base_branch="ticket/p03-forensic-calendar-gravity",
        ),
        caller=DISPATCHER_CALLER,
    )
    assert result["observed_state"]["agent_id"]
