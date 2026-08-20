"""Anonymous denial at the trusted transport boundary (no injected caller)."""

from __future__ import annotations

import pytest
from tokens import DISPATCHER_CALLER

from personal_enigma.cursor_relay.config import RelayConfig
from personal_enigma.cursor_relay.cursor_client import MockCursorClient
from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.mcp_server import McpStdioServer
from personal_enigma.cursor_relay.relay import MCP_TOOLS, RelayService


@pytest.mark.parametrize("tool", MCP_TOOLS)
def test_anonymous_denied_for_every_tool(service: RelayService, tool: str) -> None:
    result = service.invoke(tool, {}, caller=None)
    validate_handoff(result)
    assert result["recommended_action"]["kind"] == "stop_needs_human"
    assert "unauthenticated" in result["recommended_action"]["rationale"]
    deny = [r for r in service.audit.records if r["decision"] == "deny"]
    assert deny
    assert deny[-1]["caller_id"] == "anonymous"


def test_status_never_anonymous(service: RelayService) -> None:
    # Explicit regression: status is read-only authz but still authenticated.
    result = service.invoke("status", {"agent_id": "bc-x"}, caller=None)
    assert result["requires_oscar"]["required"] is True
    ok = service.invoke(
        "status",
        {"agent_id": "bc-missing"},
        caller=DISPATCHER_CALLER,
    )
    # authenticated path may error on missing agent — but not as unauthenticated
    assert "unauthenticated" not in ok["recommended_action"]["rationale"]


@pytest.mark.parametrize("tool", MCP_TOOLS)
def test_mcp_transport_anonymous_without_tunnel_caller(tool: str) -> None:
    """Trusted transport without RELAY_TUNNEL_CALLER denies every tool."""

    service = RelayService(RelayConfig(tunnel_caller=None), cursor=MockCursorClient())
    server = McpStdioServer(service)
    call = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": {"agent_id": "bc-x", "run_id": "r"}},
        }
    )
    assert call is not None
    handoff = call["result"]["structuredContent"]
    validate_handoff(handoff)
    assert "unauthenticated" in handoff["recommended_action"]["rationale"]
    assert any(r["caller_id"] == "anonymous" for r in service.audit.records)
