"""Approval policy allow/deny matrix."""

from __future__ import annotations

from tokens import APPROVER_CALLER, DISPATCHER_CALLER, READER_CALLER

from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.relay import RelayService

BASE_DISPATCH = {
    "idempotency_key": "apr-1",
    "repository": "oscarhilton/enigma-assistant-",
    "environment": "enigma-assistant-",
    "head_branch": "ticket/cloud-02-cursor-relay-mcp",
    "prompt": "read-only conductor",
    "job_brief": {"authorization": {"dry_run": False, "allow_push": True}},
}


def test_reader_cannot_dispatch(service: RelayService) -> None:
    result = service.invoke("dispatch", BASE_DISPATCH, caller=READER_CALLER)
    validate_handoff(result)
    assert "approval_denied" in result["recommended_action"]["rationale"]


def test_dispatcher_can_dispatch(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        {**BASE_DISPATCH, "idempotency_key": "apr-ok"},
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert result["recommended_action"]["kind"] == "no_action"
    assert result["observed_state"]["agent_id"]


def test_reader_can_status_after_dispatch(service: RelayService) -> None:
    dispatched = service.invoke(
        "dispatch",
        {**BASE_DISPATCH, "idempotency_key": "apr-status"},
        caller=DISPATCHER_CALLER,
    )
    agent_id = dispatched["observed_state"]["agent_id"]
    result = service.invoke(
        "status",
        {"agent_id": agent_id},
        caller=READER_CALLER,
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
        caller=DISPATCHER_CALLER,
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
            "job_brief": {"authorization": {"dry_run": False, "allow_push": True}},
        },
        caller=APPROVER_CALLER,
    )
    validate_handoff(result)
    assert result["recommended_action"]["kind"] == "request_review"
    assert result["observed_state"].get("merge") is False
    assert result["observed_state"]["agent_id"]


def test_merge_always_denied(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        {**BASE_DISPATCH, "idempotency_key": "merge-no", "merge": True},
        caller=DISPATCHER_CALLER,
    )
    assert "merge_forbidden" in result["recommended_action"]["rationale"]


def test_auto_pr_requires_brief_auth(service: RelayService) -> None:
    result = service.invoke(
        "dispatch",
        {
            **BASE_DISPATCH,
            "idempotency_key": "pr-no",
            "auto_create_pr": True,
            "job_brief": {"authorization": {"dry_run": False, "allow_push": True}},
        },
        caller=DISPATCHER_CALLER,
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
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert result["observed_state"]["agent_id"]


def test_cancel_requires_approver(service: RelayService) -> None:
    dispatched = service.invoke(
        "dispatch",
        {**BASE_DISPATCH, "idempotency_key": "cancel-setup"},
        caller=DISPATCHER_CALLER,
    )
    agent_id = dispatched["observed_state"]["agent_id"]
    run_id = dispatched["observed_state"]["run_id"]
    denied = service.invoke(
        "cancel",
        {"agent_id": agent_id, "run_id": run_id},
        caller=DISPATCHER_CALLER,
    )
    assert "approval_denied" in denied["recommended_action"]["rationale"]
    allowed = service.invoke(
        "cancel",
        {"agent_id": agent_id, "run_id": run_id},
        caller=APPROVER_CALLER,
    )
    validate_handoff(allowed)
    assert "Cancelled" in allowed["recommended_action"]["rationale"]
