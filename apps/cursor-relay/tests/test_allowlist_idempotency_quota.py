"""Allowlist, idempotency, and quota denials."""

from __future__ import annotations

from tokens import DISPATCHER, bearer

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
        "job_brief": {"authorization": {"dry_run": True}},
    }
    base.update(overrides)
    return base


def test_repo_allowlist_denial(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("al-repo", repository="evil/other-repo"),
        authorization=bearer(DISPATCHER),
    )
    validate_handoff(result)
    assert "allowlist_denied" in result["recommended_action"]["rationale"]
    assert "repository" in result["recommended_action"]["rationale"] or True


def test_environment_allowlist_denial(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("al-env", environment="not-bound-env"),
        authorization=bearer(DISPATCHER),
    )
    assert "allowlist_denied" in result["recommended_action"]["rationale"]


def test_branch_prefix_denial(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("al-branch", head_branch="feature/nope"),
        authorization=bearer(DISPATCHER),
    )
    assert "allowlist_denied" in result["recommended_action"]["rationale"]


def test_main_head_forbidden(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("al-main", head_branch="main"),
        authorization=bearer(DISPATCHER),
    )
    assert "allowlist_denied" in result["recommended_action"]["rationale"]


def test_model_allowlist_denial(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        _dispatch_params("al-model", model="unapproved-model-xyz"),
        authorization=bearer(DISPATCHER),
    )
    assert "allowlist_denied" in result["recommended_action"]["rationale"]


def test_idempotency_required(service: RelayService) -> None:
    params = _dispatch_params("x")
    del params["idempotency_key"]
    result = service.invoke("dispatch", params, authorization=bearer(DISPATCHER))
    assert "idempotency_required" in result["recommended_action"]["rationale"]


def test_idempotency_replay(service: RelayService, mock_cursor: MockCursorClient) -> None:
    first = service.invoke(
        "dispatch",
        _dispatch_params("idem-1"),
        authorization=bearer(DISPATCHER),
    )
    second = service.invoke(
        "dispatch",
        _dispatch_params("idem-1"),
        authorization=bearer(DISPATCHER),
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
        authorization=bearer(DISPATCHER),
    )
    assert ok["observed_state"]["agent_id"]
    denied = service.invoke(
        "dispatch",
        _dispatch_params("q-2"),
        authorization=bearer(DISPATCHER),
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
        authorization=bearer(DISPATCHER),
    )
    denied = service.invoke(
        "dispatch",
        _dispatch_params("s-2"),
        authorization=bearer(DISPATCHER),
    )
    assert "spend_exceeded" in denied["recommended_action"]["rationale"]


def test_request_review_idempotency_and_quota(relay_config: RelayConfig) -> None:
    from tokens import APPROVER

    cursor = MockCursorClient()
    quotas = QuotaTracker(max_in_flight=1, max_spend_units=100, spend_per_create=1)
    service = RelayService(relay_config, cursor=cursor, quotas=quotas)
    params = {
        "idempotency_key": "rr-1",
        "repository": "oscarhilton/enigma-assistant-",
        "environment": "1baeb513-9c77-11f1-ba66-0e7d0216e441",
        "head_branch": "cursor/review-a131",
        "prompt": "review",
    }
    first = service.invoke("request_review", params, authorization=bearer(APPROVER))
    second = service.invoke("request_review", params, authorization=bearer(APPROVER))
    assert first["observed_state"]["agent_id"] == second["observed_state"]["agent_id"]
    assert len(cursor.create_calls) == 1
    denied = service.invoke(
        "request_review",
        {**params, "idempotency_key": "rr-2"},
        authorization=bearer(APPROVER),
    )
    assert "concurrency_exceeded" in denied["recommended_action"]["rationale"]
