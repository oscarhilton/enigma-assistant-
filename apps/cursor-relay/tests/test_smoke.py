"""End-to-end smoke against MockCursorClient (no live CURSOR_API_KEY)."""

from __future__ import annotations

import json

from tokens import APPROVER, DISPATCHER, bearer

from personal_enigma.cursor_relay.audit import hash_prompt
from personal_enigma.cursor_relay.cursor_client import MockCursorClient
from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.mcp_server import McpStdioServer
from personal_enigma.cursor_relay.relay import RelayService


def test_dispatch_status_cancel_smoke(service: RelayService, mock_cursor: MockCursorClient) -> None:
    prompt = "Read-only conductor against allowlisted branch"
    dispatched = service.invoke(
        "dispatch",
        {
            "idempotency_key": "smoke-1",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": "1baeb513-9c77-11f1-ba66-0e7d0216e441",
            "head_branch": "cursor/cloud-02-smoke-a131",
            "base_branch": "main",
            "prompt": prompt,
            "ticket_path": "tickets/platform/CLOUD-02-cursor-relay-mcp.md",
            "ticket_ids": ["CLOUD-02"],
            "job_brief": {"authorization": {"dry_run": True}},
        },
        authorization=bearer(DISPATCHER),
    )
    validate_handoff(dispatched)
    agent_id = dispatched["observed_state"]["agent_id"]
    run_id = dispatched["observed_state"]["run_id"]

    status = service.invoke(
        "status",
        {"agent_id": agent_id, "run_id": run_id, "ticket_ids": ["CLOUD-02"]},
        authorization=bearer(DISPATCHER),
    )
    validate_handoff(status)
    assert status["observed_state"]["lifecycle_status"] in {"CREATING", "ACTIVE", "UNKNOWN"}

    cancelled = service.invoke(
        "cancel",
        {"agent_id": agent_id, "run_id": run_id, "ticket_ids": ["CLOUD-02"]},
        authorization=bearer(APPROVER),
    )
    validate_handoff(cancelled)
    assert mock_cursor.cancel_calls == [(agent_id, run_id)]

    # Audit has caller, agent, run, prompt hash, usage
    allows = [r for r in service.audit.records if r["decision"] == "allow"]
    assert any(r["tool"] == "dispatch" and r["prompt_hash"] == hash_prompt(prompt) for r in allows)
    assert any(r["tool"] == "status" and r["agent_id"] == agent_id for r in allows)
    assert any(r.get("usage") for r in allows if r["tool"] == "dispatch")


def test_mcp_tools_list_and_call(service: RelayService) -> None:
    server = McpStdioServer(service)
    listed = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert listed is not None
    names = {t["name"] for t in listed["result"]["tools"]}
    assert names == {"dispatch", "status", "follow_up", "request_review", "cancel"}

    call = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "dispatch",
                "arguments": {
                    "authorization": bearer(DISPATCHER),
                    "idempotency_key": "mcp-1",
                    "repository": "oscarhilton/enigma-assistant-",
                    "environment": "enigma-assistant-",
                    "head_branch": "agent/mcp-smoke",
                    "prompt": "mcp smoke",
                    "job_brief": {"authorization": {"dry_run": True}},
                },
            },
        }
    )
    assert call is not None
    handoff = call["result"]["structuredContent"]
    validate_handoff(handoff)
    # Default content is structured JSON, not a raw transcript dump of secrets
    body = call["result"]["content"][0]["text"]
    assert "CURSOR_API_KEY" not in body
    parsed = json.loads(body)
    assert parsed["observed_state"]["agent_id"]


def test_follow_up_write_path(service: RelayService, mock_cursor: MockCursorClient) -> None:
    dispatched = service.invoke(
        "dispatch",
        {
            "idempotency_key": "fu-setup",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": "enigma-assistant-",
            "head_branch": "ticket/cloud-02-cursor-relay-mcp",
            "prompt": "setup",
            "job_brief": {"authorization": {"dry_run": True}},
        },
        authorization=bearer(DISPATCHER),
    )
    agent_id = dispatched["observed_state"]["agent_id"]
    result = service.invoke(
        "follow_up",
        {
            "idempotency_key": "fu-1",
            "agent_id": agent_id,
            "prompt": "continue",
            "job_brief": {"authorization": {"dry_run": True}},
        },
        authorization=bearer(DISPATCHER),
    )
    validate_handoff(result)
    assert mock_cursor.run_calls
    assert result["observed_state"]["run_id"] != dispatched["observed_state"]["run_id"]


def test_chatgpt_credentials_rejected_as_cursor_key() -> None:
    from personal_enigma.cursor_relay.config import load_config_from_env

    try:
        load_config_from_env(
            {
                "CURSOR_API_KEY": "shared-secret",
                "CHATGPT_API_KEY": "shared-secret",
                "RELAY_AUTH_TOKENS": "{}",
            }
        )
        raised = False
    except ValueError:
        raised = True
    assert raised
