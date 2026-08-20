"""Negative tests: MCP discovery/calls never expose or accept auth secrets."""

from __future__ import annotations

import json

from tokens import DISPATCHER_CALLER

from personal_enigma.cursor_relay.auth import MODEL_SUPPLIED_SECRET_KEYS
from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.mcp_server import (
    TOOL_SCHEMAS,
    McpStdioServer,
    _schema_mentions_secrets,
)
from personal_enigma.cursor_relay.relay import MCP_TOOLS, RelayService


def test_tools_list_schemas_have_no_credential_properties() -> None:
    hits = _schema_mentions_secrets(TOOL_SCHEMAS)
    assert hits == []
    for tool in TOOL_SCHEMAS:
        props = (tool.get("inputSchema") or {}).get("properties") or {}
        required = (tool.get("inputSchema") or {}).get("required") or []
        for key in list(props) + list(required):
            assert str(key).lower() not in MODEL_SUPPLIED_SECRET_KEYS
        blob = json.dumps(tool).lower()
        assert "bearer" not in blob
        assert "authorization" not in blob
        assert "api_key" not in blob
        assert "cursor_api_key" not in blob


def test_mcp_tools_list_response_has_no_secrets(service: RelayService) -> None:
    server = McpStdioServer(service)
    listed = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert listed is not None
    body = json.dumps(listed).lower()
    assert "bearer" not in body
    assert "authorization" not in body
    assert "api_key" not in body
    assert "cursor_api_key" not in body
    assert "test-token" not in body


def test_mcp_rejects_model_supplied_authorization(service: RelayService) -> None:
    server = McpStdioServer(service)
    call = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "status",
                "arguments": {
                    "authorization": "Bearer totally-secret",
                    "agent_id": "bc-x",
                },
            },
        }
    )
    assert call is not None
    handoff = call["result"]["structuredContent"]
    validate_handoff(handoff)
    assert "model_supplied_secret" in handoff["recommended_action"]["rationale"]
    assert "totally-secret" not in json.dumps(handoff)
    assert "Bearer" not in json.dumps(handoff)


def test_mcp_rejects_model_supplied_api_key(service: RelayService) -> None:
    server = McpStdioServer(service)
    call = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "dispatch",
                "arguments": {
                    "api_key": "sk-fake",
                    "idempotency_key": "nope",
                    "repository": "oscarhilton/enigma-assistant-",
                    "environment": "enigma-assistant-",
                    "head_branch": "ticket/cloud-02-cursor-relay-mcp",
                },
            },
        }
    )
    assert call is not None
    handoff = call["result"]["structuredContent"]
    assert "model_supplied_secret" in handoff["recommended_action"]["rationale"]
    assert "sk-fake" not in json.dumps(handoff)


def test_mcp_call_without_secrets_uses_tunnel_caller(
    service: RelayService,
) -> None:
    server = McpStdioServer(service)
    call = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "dispatch",
                "arguments": {
                    "idempotency_key": "tunnel-ok",
                    "repository": "oscarhilton/enigma-assistant-",
                    "environment": "enigma-assistant-",
                    "head_branch": "ticket/cloud-02-cursor-relay-mcp",
                    "prompt": "no secrets",
                    "job_brief": {"authorization": {"dry_run": True}},
                },
            },
        }
    )
    assert call is not None
    handoff = call["result"]["structuredContent"]
    validate_handoff(handoff)
    assert handoff["observed_state"]["agent_id"]
    allows = [r for r in service.audit.records if r["decision"] == "allow"]
    assert any(r["caller_id"] == "tunnel-pilot" for r in allows)


def test_internal_invoke_still_attributes_explicit_caller(service: RelayService) -> None:
    """Role tests inject callers in-process — never via MCP argument schemas."""

    result = service.invoke(
        "dispatch",
        {
            "idempotency_key": "attr-1",
            "repository": "oscarhilton/enigma-assistant-",
            "environment": "enigma-assistant-",
            "head_branch": "ticket/cloud-02-cursor-relay-mcp",
            "prompt": "x",
            "job_brief": {"authorization": {"dry_run": True}},
        },
        caller=DISPATCHER_CALLER,
    )
    assert result["observed_state"]["agent_id"]
    assert any(
        r["caller_id"] == "chatgpt-dispatcher" and r["decision"] == "allow"
        for r in service.audit.records
    )


def test_all_mcp_tools_covered_by_secret_schema_scan() -> None:
    names = {t["name"] for t in TOOL_SCHEMAS}
    assert names == set(MCP_TOOLS)
