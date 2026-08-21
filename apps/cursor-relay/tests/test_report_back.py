"""CLOUD-04 agent report-back: result MCP tool, stream/get_run fallback, cache."""

from __future__ import annotations

import json

from tokens import DISPATCHER_CALLER, READER_CALLER

from personal_enigma.cursor_relay.cursor_client import (
    MockCursorClient,
    StreamRunOutcome,
    _parse_sse_run_stream,
)
from personal_enigma.cursor_relay.handoff import strip_secrets, validate_handoff
from personal_enigma.cursor_relay.mcp_server import McpStdioServer
from personal_enigma.cursor_relay.relay import RelayService
from personal_enigma.cursor_relay.report_back import (
    build_result_handoff,
    is_terminal_status,
    resolve_terminal_snapshot,
    snapshot_from_get_run,
)
from personal_enigma.cursor_relay.result_store import ResultStore, TerminalRunSnapshot


def _finished_run(
    mock: MockCursorClient,
    *,
    agent_id: str,
    run_id: str,
    result: str = "Implemented CLOUD-04 with tests passing.",
    pr_url: str | None = "https://github.com/oscarhilton/enigma-assistant-/pull/999",
) -> None:
    branch = "cursor/cloud-04-agent-report-back-1a4e"
    git_entry: dict[str, str] = {"branch": branch}
    if pr_url:
        git_entry["prUrl"] = pr_url
    mock.runs[run_id] = {
        "id": run_id,
        "agentId": agent_id,
        "status": "FINISHED",
        "durationMs": 54321,
        "result": result,
        "git": {"branches": [git_entry]},
    }
    mock.agents[agent_id] = {
        "id": agent_id,
        "status": "ACTIVE",
        "latestRunId": run_id,
        "url": f"https://cursor.com/agents/{agent_id}",
    }


def test_parse_sse_result_event() -> None:
    payload = json.dumps(
        {
            "runId": "run-1",
            "status": "FINISHED",
            "text": "Done.",
            "durationMs": 1200,
            "git": {"branches": [{"branch": "cursor/test"}]},
        }
    )
    lines = [
        "event: heartbeat",
        "data: {}",
        "",
        "event: result",
        f"data: {payload}",
        "",
        "event: done",
        "data: {}",
        "",
    ]
    outcome = _parse_sse_run_stream(lines)
    assert outcome.status == "FINISHED"
    assert outcome.text == "Done."
    assert outcome.duration_ms == 1200
    assert outcome.git == {"branches": [{"branch": "cursor/test"}]}


def test_parse_sse_error_event() -> None:
    lines = [
        "event: error",
        'data: {"code": "worker_disconnected", "message": "Worker lost"}',
        "",
    ]
    outcome = _parse_sse_run_stream(lines)
    assert outcome.status == "ERROR"
    assert outcome.stream_error == {
        "code": "worker_disconnected",
        "message": "Worker lost",
    }


def test_terminal_result_via_stream(service: RelayService, mock_cursor: MockCursorClient) -> None:
    dispatched = service.invoke(
        "dispatch",
        {
            "idempotency_key": "rb-dispatch",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": "enigma-assistant-",
            "head_branch": "ticket/cloud-04-agent-report-back",
            "prompt": "implement report-back",
            "ticket_ids": ["CLOUD-04"],
            "job_brief": {"authorization": {"dry_run": False, "allow_push": True}},
        },
        caller=DISPATCHER_CALLER,
    )
    agent_id = dispatched["observed_state"]["agent_id"]
    run_id = dispatched["observed_state"]["run_id"]
    _finished_run(mock_cursor, agent_id=agent_id, run_id=run_id)

    handoff = service.invoke(
        "result",
        {"agent_id": agent_id, "run_id": run_id, "ticket_ids": ["CLOUD-04"]},
        caller=READER_CALLER,
    )
    validate_handoff(handoff)
    obs = handoff["observed_state"]
    assert obs["terminal"] is True
    assert obs["run_status"] == "FINISHED"
    assert obs["duration_ms"] == 54321
    assert obs["final_result"] == "Implemented CLOUD-04 with tests passing."
    assert obs["agent_id"] == agent_id
    assert obs["run_id"] == run_id
    assert obs["ticket_ids"] == ["CLOUD-04"]
    assert obs["result_source"] == "stream"
    assert obs["git_branches"] == ["cursor/cloud-04-agent-report-back-1a4e"]
    assert obs["pr_urls"] == ["https://github.com/oscarhilton/enigma-assistant-/pull/999"]
    assert handoff["observed_state"]["open_prs"][0]["number"] == 999
    assert mock_cursor.stream_calls == [(agent_id, run_id)]


def test_stream_expired_falls_back_to_get_run(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    agent_id, run_id = "bc-fallback", "run-fallback"
    _finished_run(
        mock_cursor,
        agent_id=agent_id,
        run_id=run_id,
        result="GET fallback body",
    )
    mock_cursor.stream_expired_for.add((agent_id, run_id))

    handoff = service.invoke(
        "result",
        {"agent_id": agent_id, "run_id": run_id, "ticket_ids": ["CLOUD-04"]},
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(handoff)
    obs = handoff["observed_state"]
    assert obs["terminal"] is True
    assert obs["result_source"] == "get_run"
    assert obs["final_result"] == "GET fallback body"
    assert obs["duration_ms"] == 54321


def test_result_cache_avoids_repeat_stream(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    agent_id, run_id = "bc-cache", "run-cache"
    _finished_run(mock_cursor, agent_id=agent_id, run_id=run_id)
    params = {"agent_id": agent_id, "run_id": run_id, "ticket_ids": ["CLOUD-04"]}

    first = service.invoke("result", params, caller=DISPATCHER_CALLER)
    second = service.invoke("result", params, caller=DISPATCHER_CALLER)
    validate_handoff(first)
    validate_handoff(second)
    assert first["observed_state"]["result_source"] == "stream"
    assert second["observed_state"]["result_source"] == "cache"
    assert mock_cursor.stream_calls.count((agent_id, run_id)) == 1


def test_non_terminal_run_returns_pending(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    dispatched = service.invoke(
        "dispatch",
        {
            "idempotency_key": "rb-pending",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": "enigma-assistant-",
            "head_branch": "ticket/cloud-04-agent-report-back",
            "prompt": "still running",
            "ticket_ids": ["CLOUD-04"],
            "job_brief": {"authorization": {"dry_run": False, "allow_push": True}},
        },
        caller=DISPATCHER_CALLER,
    )
    agent_id = dispatched["observed_state"]["agent_id"]
    run_id = dispatched["observed_state"]["run_id"]

    handoff = service.invoke(
        "result",
        {"agent_id": agent_id, "run_id": run_id, "ticket_ids": ["CLOUD-04"]},
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(handoff)
    obs = handoff["observed_state"]
    assert obs["terminal"] is False
    assert obs["run_status"] == "CREATING"
    assert obs["final_result"] is None
    assert obs["duration_ms"] is None
    assert mock_cursor.stream_calls == []


def test_error_run_uses_stream_error_payload(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    agent_id, run_id = "bc-err", "run-err"
    mock_cursor.runs[run_id] = {
        "id": run_id,
        "agentId": agent_id,
        "status": "ERROR",
        "durationMs": 900,
        "result": None,
        "error": None,
        "stream_error": {"code": "worker_disconnected", "message": "Worker lost"},
    }
    mock_cursor.agents[agent_id] = {"id": agent_id, "latestRunId": run_id}

    handoff = service.invoke(
        "result",
        {"agent_id": agent_id, "run_id": run_id, "ticket_ids": ["CLOUD-04"]},
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(handoff)
    obs = handoff["observed_state"]
    assert obs["terminal"] is True
    assert obs["run_status"] == "ERROR"
    assert obs["stream_error"] == {
        "code": "worker_disconnected",
        "message": "Worker lost",
    }


def test_cancelled_terminal_state(service: RelayService, mock_cursor: MockCursorClient) -> None:
    agent_id, run_id = "bc-cancel", "run-cancel"
    mock_cursor.runs[run_id] = {
        "id": run_id,
        "agentId": agent_id,
        "status": "CANCELLED",
        "durationMs": 100,
        "result": None,
    }
    mock_cursor.agents[agent_id] = {"id": agent_id, "latestRunId": run_id}

    handoff = service.invoke(
        "result",
        {"agent_id": agent_id, "run_id": run_id},
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(handoff)
    assert handoff["observed_state"]["terminal"] is True
    assert handoff["observed_state"]["run_status"] == "CANCELLED"


def test_result_strips_secrets_from_final_text() -> None:
    snapshot = TerminalRunSnapshot(
        agent_id="bc-1",
        run_id="run-1",
        run_status="FINISHED",
        final_result="Done. key_sk-cur_secret_here should redact",
        duration_ms=1,
        git_branches=["cursor/x"],
        pr_urls=[],
        result_source="stream",
    )
    handoff = build_result_handoff(
        snapshot=snapshot,
        agent_id="bc-1",
        run_id="run-1",
        ticket_ids=["CLOUD-04"],
        run_status="FINISHED",
        terminal=True,
    )
    scrubbed = strip_secrets(handoff)
    assert "sk-cur" not in json.dumps(scrubbed).lower()
    assert scrubbed["observed_state"]["final_result"] == "[redacted]"


def test_result_cursor_outage_schema_valid(
    service: RelayService, mock_cursor: MockCursorClient
) -> None:
    mock_cursor.fail_next = "timeout"
    result = service.invoke(
        "result",
        {"agent_id": "bc-x", "run_id": "run-x"},
        caller=DISPATCHER_CALLER,
    )
    validate_handoff(result)
    assert result["recommended_action"]["kind"] == "stop_needs_human"
    assert "cursor_timeout" in result["recommended_action"]["rationale"]


def test_anonymous_result_denied(service: RelayService) -> None:
    result = service.invoke("result", {"agent_id": "bc-x", "run_id": "run-x"}, caller=None)
    validate_handoff(result)
    assert "unauthenticated" in result["recommended_action"]["rationale"]


def test_mcp_result_tool_listed(service: RelayService) -> None:
    server = McpStdioServer(service)
    listed = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert listed is not None
    names = {t["name"] for t in listed["result"]["tools"]}
    assert "result" in names


def test_is_terminal_status_matrix() -> None:
    assert is_terminal_status("FINISHED")
    assert is_terminal_status("ERROR")
    assert is_terminal_status("CANCELLED")
    assert is_terminal_status("EXPIRED")
    assert not is_terminal_status("RUNNING")
    assert not is_terminal_status("CREATING")


def test_snapshot_from_get_run_extracts_metadata() -> None:
    snap = snapshot_from_get_run(
        agent_id="bc-1",
        run_id="run-1",
        run={
            "status": "FINISHED",
            "result": "hello",
            "durationMs": 42,
            "git": {
                "branches": [
                    {
                        "branch": "cursor/foo",
                        "prUrl": "https://github.com/org/repo/pull/7",
                    }
                ]
            },
        },
    )
    assert snap.final_result == "hello"
    assert snap.duration_ms == 42
    assert snap.git_branches == ["cursor/foo"]
    assert snap.pr_urls == ["https://github.com/org/repo/pull/7"]


def test_resolve_terminal_snapshot_unit(mock_cursor: MockCursorClient) -> None:
    store = ResultStore()
    agent_id, run_id = "bc-unit", "run-unit"
    _finished_run(mock_cursor, agent_id=agent_id, run_id=run_id, result="unit")
    snap, status, terminal = resolve_terminal_snapshot(
        cursor=mock_cursor,
        result_store=store,
        agent_id=agent_id,
        run_id=run_id,
    )
    assert terminal is True
    assert status == "FINISHED"
    assert snap is not None
    assert snap.final_result == "unit"
    assert store.get(agent_id, run_id) is not None


def test_stream_run_outcome_dataclass() -> None:
    outcome = StreamRunOutcome(status="FINISHED", text="x", duration_ms=5)
    assert outcome.stream_error is None
