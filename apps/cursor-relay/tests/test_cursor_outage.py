"""Cursor outage / timeout → schema-valid failure handoffs."""

from __future__ import annotations

from tokens import DISPATCHER, bearer

from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.relay import RelayService


def _dispatch(key: str) -> dict:
    return {
        "idempotency_key": key,
        "repository": "oscarhilton/enigma-assistant-",
        "environment": "enigma-assistant-",
        "head_branch": "ticket/cloud-02-cursor-relay-mcp",
        "prompt": "hello",
        "job_brief": {"authorization": {"dry_run": True}},
    }


def test_cursor_timeout_handoff(service: RelayService, mock_cursor) -> None:
    mock_cursor.fail_next = "timeout"
    result = service.invoke(
        "dispatch",
        _dispatch("out-timeout"),
        authorization=bearer(DISPATCHER),
    )
    validate_handoff(result)
    assert result["recommended_action"]["kind"] == "stop_needs_human"
    assert "cursor_timeout" in result["recommended_action"]["rationale"]
    assert "CURSOR_API_KEY" not in str(result)


def test_cursor_http_outage_handoff(service: RelayService, mock_cursor) -> None:
    mock_cursor.fail_next = "http_503"
    result = service.invoke(
        "dispatch",
        _dispatch("out-503"),
        authorization=bearer(DISPATCHER),
    )
    validate_handoff(result)
    assert "cursor_http_error" in result["recommended_action"]["rationale"]


def test_cursor_transport_error_handoff(service: RelayService, mock_cursor) -> None:
    mock_cursor.fail_next = "transport"
    result = service.invoke(
        "status",
        {"agent_id": "bc-x"},
        authorization=bearer(DISPATCHER),
    )
    # status will call get_agent which fails
    validate_handoff(result)
    assert "cursor_transport_error" in result["recommended_action"]["rationale"]
