"""Anonymous / unauthenticated denial for every MCP tool."""

from __future__ import annotations

import pytest
from tokens import DISPATCHER, bearer

from personal_enigma.cursor_relay.handoff import validate_handoff
from personal_enigma.cursor_relay.relay import MCP_TOOLS, RelayService


@pytest.mark.parametrize("tool", MCP_TOOLS)
def test_anonymous_denied_for_every_tool(service: RelayService, tool: str) -> None:
    result = service.invoke(tool, {}, authorization=None)
    validate_handoff(result)
    assert result["recommended_action"]["kind"] == "stop_needs_human"
    assert "unauthenticated" in result["recommended_action"]["rationale"]
    deny = [r for r in service.audit.records if r["decision"] == "deny"]
    assert deny
    assert deny[-1]["caller_id"] == "anonymous"


@pytest.mark.parametrize("tool", MCP_TOOLS)
def test_invalid_bearer_denied(service: RelayService, tool: str) -> None:
    result = service.invoke(tool, {}, authorization="Bearer totally-unknown")
    validate_handoff(result)
    assert "unauthenticated" in result["recommended_action"]["rationale"]


def test_status_never_anonymous(service: RelayService) -> None:
    # Explicit regression: status is read-only authz but still authenticated.
    result = service.invoke("status", {"agent_id": "bc-x"}, authorization=None)
    assert result["requires_oscar"]["required"] is True
    ok = service.invoke(
        "status",
        {"agent_id": "bc-missing"},
        authorization=bearer(DISPATCHER),
    )
    # authenticated path may error on missing agent — but not as unauthenticated
    assert "unauthenticated" not in ok["recommended_action"]["rationale"]
