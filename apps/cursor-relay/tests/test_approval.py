"""Approval policy allow/deny matrix."""

from __future__ import annotations

from tokens import APPROVER, DISPATCHER, READER, bearer

from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.relay import RelayService

BASE_DISPATCH = {
    "idempotency_key": "apr-1",
    "repository": "oscarhilton/enigma-assistant-",
    "environment": "enigma-assistant-",
    "head_branch": "ticket/cloud-02-cursor-relay-mcp",
    "prompt": "read-only conductor",
    "job_brief": {"authorization": {"dry_run": True}},
}


def test_reader_cannot_dispatch(service: RelayService) -> None:
    result = service.invoke("dispatch", BASE_DISPATCH, authorization=bearer(READER))
    validate_handoff(result)
    assert "approval_denied" in result["recommended_action"]["rationale"]


def test_dispatcher_can_dispatch(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        {**BASE_DISPATCH, "idempotency_key": "apr-ok"},
        authorization=bearer(DISPATCHER),
    )
    validate_handoff(result)
    assert result["recommended_action"]["kind"] == "no_action"
    assert result["observed_state"]["agent_id"]


def test_reader_can_status_after_dispatch(service: RelayService) -> None:
    dispatched = service.invoke(
        "dispatch",
        {**BASE_DISPATCH, "idempotency_key": "apr-status"},
        authorization=bearer(DISPATCHER),
    )
    agent_id = dispatched["observed_state"]["agent_id"]
    result = service.invoke(
        "status",
        {"agent_id": agent_id},
        authorization=bearer(READER),
    )
    validate_handoff(result)
    assert "Denied" not in result["recommended_action"]["rationale"]


def test_dispatcher_cannot_request_review(service: RelayService) -> None:
    result = service.invoke(
        "request_review",
        {
            "idempotency_key": "rev-deny",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": "enigma-assistant-",
            "head_branch": "cursor/review-branch-a131",
            "prompt": "review please",
        },
        authorization=bearer(DISPATCHER),
    )
    validate_handoff(result)
    assert "approval_denied" in result["recommended_action"]["rationale"]


def test_approver_can_request_review(service: RelayService) -> None:
    result = service.invoke(
        "request_review",
        {
            "idempotency_key": "rev-ok",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": "enigma-assistant-",
            "head_branch": "cursor/review-branch-a131",
            "prompt": "review please",
        },
        authorization=bearer(APPROVER),
    )
    validate_handoff(result)
    assert result["recommended_action"]["kind"] == "request_review"
    assert result["observed_state"].get("merge") is False


def test_merge_always_denied(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        {**BASE_DISPATCH, "idempotency_key": "merge-no", "merge": True},
        authorization=bearer(DISPATCHER),
    )
    assert "merge_forbidden" in result["recommended_action"]["rationale"]


def test_auto_pr_requires_brief_auth(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        {
            **BASE_DISPATCH,
            "idempotency_key": "pr-no",
            "auto_create_pr": True,
            "job_brief": {"authorization": {"dry_run": True}},
        },
        authorization=bearer(DISPATCHER),
    )
    assert "pr_not_authorized" in result["recommended_action"]["rationale"]


def test_auto_pr_allowed_with_brief(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        {
            **BASE_DISPATCH,
            "idempotency_key": "pr-yes",
            "auto_create_pr": True,
            "job_brief": {
                "authorization": {
                    "dry_run": False,
                    "allow_open_pr": True,
                    "allow_push": True,
                }
            },
        },
        authorization=bearer(DISPATCHER),
    )
    validate_handoff(result)
    assert result["observed_state"]["agent_id"]


def test_cancel_requires_approver(service: RelayService) -> None:
    dispatched = service.invoke(
        "dispatch",
        {**BASE_DISPATCH, "idempotency_key": "cancel-setup"},
        authorization=bearer(DISPATCHER),
    )
    agent_id = dispatched["observed_state"]["agent_id"]
    run_id = dispatched["observed_state"]["run_id"]
    denied = service.invoke(
        "cancel",
        {"agent_id": agent_id, "run_id": run_id},
        authorization=bearer(DISPATCHER),
    )
    assert "approval_denied" in denied["recommended_action"]["rationale"]
    allowed = service.invoke(
        "cancel",
        {"agent_id": agent_id, "run_id": run_id},
        authorization=bearer(APPROVER),
    )
    validate_handoff(allowed)
    assert "Cancelled" in allowed["recommended_action"]["rationale"]
