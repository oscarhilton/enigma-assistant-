"""Completed review runs expose a structured verdict on status; absence is quiet."""

from __future__ import annotations

import json

from tokens import APPROVER_CALLER, DISPATCHER_CALLER, READER_CALLER

from personal_enigma.cursor_relay.cursor_client import MockCursorClient
from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.relay import RelayService
from personal_enigma.cursor_relay.review_outcome import extract_review_outcome

LIVE_AUTH = {"authorization": {"dry_run": False, "allow_push": True}}


def _review_handoff(*, verdict: str | None = None, kind: str = "no_action") -> str:
    observed: dict[str, object] = {"relay_tool": "request_review", "merge": False}
    if verdict is not None:
        observed["review_verdict"] = verdict
    return json.dumps(
        {
            "observed_state": observed,
            "evidence": [{"kind": "note", "summary": "Secret-scan clean; one nits-level finding"}],
            "scope_classification": "in_ticket",
            "recommended_action": {"kind": kind, "rationale": "review complete"},
            "tests": [{"command": "uv run pytest apps/cursor-relay/tests", "passed": True}],
            "residual_risks": ["host must redeploy relay"],
            "requires_oscar": {"required": kind == "stop_needs_human", "reasons": []},
        }
    )


def _start_review(service: RelayService) -> tuple[str, str]:
    created = service.invoke(
        "request_review",
        {
            "idempotency_key": "rr-outcome-1",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": "enigma-assistant-",
            "head_branch": "cursor/review-outcome",
            "prompt": "review",
            "job_brief": LIVE_AUTH,
        },
        caller=APPROVER_CALLER,
    )
    observed = created["observed_state"]
    return str(observed["agent_id"]), str(observed["run_id"])


def test_extract_explicit_approve_from_handoff_json() -> None:
    extra = extract_review_outcome(
        run={"status": "FINISHED", "result": _review_handoff(verdict="APPROVE")},
        agent={"name": "relay-request-review"},
    )
    assert extra["review_verdict"] == "APPROVE"
    assert extra["review_findings"]
    assert extra["review_residual_risks"] == ["host must redeploy relay"]
    assert extra["review_result_source"] == "cursor_run_result"
    assert "result" not in extra


def test_extract_block_from_stop_needs_human() -> None:
    extra = extract_review_outcome(
        run={"status": "FINISHED", "result": _review_handoff(kind="stop_needs_human")},
        agent={"name": "relay-request-review"},
    )
    assert extra["review_verdict"] == "BLOCK"


def test_extract_approve_from_review_agent_no_action() -> None:
    extra = extract_review_outcome(
        run={"status": "FINISHED", "result": _review_handoff(kind="no_action")},
        agent={"name": "relay-request-review"},
    )
    assert extra["review_verdict"] == "APPROVE"


def test_extract_from_result_object_text() -> None:
    extra = extract_review_outcome(
        run={
            "status": "FINISHED",
            "result": {"text": _review_handoff(verdict="BLOCK")},
        },
        agent={"name": "relay-request-review"},
    )
    assert extra["review_verdict"] == "BLOCK"


def test_extract_absent_when_no_result() -> None:
    extra = extract_review_outcome(
        run={"status": "FINISHED"},
        agent={"name": "relay-request-review"},
    )
    assert extra == {}


def test_extract_absent_while_run_still_creating() -> None:
    extra = extract_review_outcome(
        run={"status": "CREATING", "result": _review_handoff(verdict="APPROVE")},
        agent={"name": "relay-request-review"},
    )
    assert extra == {}


def test_extract_does_not_invent_verdict_for_plain_text() -> None:
    extra = extract_review_outcome(
        run={"status": "FINISHED", "result": "Added README.md with usage examples."},
        agent={"name": "relay-request-review"},
    )
    assert extra == {}


def test_extract_does_not_treat_dispatch_no_action_as_approve() -> None:
    extra = extract_review_outcome(
        run={
            "status": "FINISHED",
            "result": json.dumps(
                {
                    "observed_state": {"relay_tool": "dispatch"},
                    "evidence": [{"kind": "note", "summary": "dispatched"}],
                    "scope_classification": "infra_only",
                    "recommended_action": {"kind": "no_action", "rationale": "ok"},
                    "tests": [],
                    "residual_risks": [],
                    "requires_oscar": {"required": False, "reasons": []},
                }
            ),
        },
        agent={"name": "relay:ticket/cloud-02"},
    )
    assert "review_verdict" not in extra


def test_status_exposes_completed_review_verdict(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    agent_id, run_id = _start_review(service)
    mock_cursor.runs[run_id]["status"] = "FINISHED"
    mock_cursor.runs[run_id]["result"] = _review_handoff(verdict="APPROVE")
    result = service.invoke(
        "status",
        {"agent_id": agent_id, "run_id": run_id},
        caller=READER_CALLER,
    )
    validate_handoff(result)
    observed = result["observed_state"]
    assert observed["lifecycle_status"] == "FINISHED"
    assert observed["review_verdict"] == "APPROVE"
    assert observed["review_findings"]
    assert observed["review_residual_risks"] == ["host must redeploy relay"]
    blob = json.dumps(result)
    assert "CURSOR_API_KEY" not in blob
    assert result["recommended_action"]["kind"] == "no_action"


def test_status_exposes_block_and_sets_requires_oscar(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    agent_id, run_id = _start_review(service)
    mock_cursor.runs[run_id]["status"] = "FINISHED"
    mock_cursor.runs[run_id]["result"] = _review_handoff(kind="stop_needs_human")
    result = service.invoke(
        "status",
        {"agent_id": agent_id, "run_id": run_id},
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert result["observed_state"]["review_verdict"] == "BLOCK"
    assert result["recommended_action"]["kind"] == "stop_needs_human"
    assert result["requires_oscar"]["required"] is True
    assert result["residual_risks"] == ["host must redeploy relay"]


def test_status_omits_review_fields_when_cursor_has_no_result(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    agent_id, run_id = _start_review(service)
    mock_cursor.runs[run_id]["status"] = "FINISHED"
    mock_cursor.runs[run_id].pop("result", None)
    result = service.invoke(
        "status",
        {"agent_id": agent_id, "run_id": run_id},
        caller=READER_CALLER,
    )
    validate_handoff(result)
    observed = result["observed_state"]
    assert observed["lifecycle_status"] == "FINISHED"
    assert "review_verdict" not in observed
    assert "review_findings" not in observed
    assert "review_residual_risks" not in observed
    assert result["recommended_action"]["kind"] == "no_action"
    assert result["requires_oscar"]["required"] is False
