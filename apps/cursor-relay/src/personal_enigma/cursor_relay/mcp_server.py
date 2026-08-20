"""Minimal MCP stdio server exposing relay tools.

Transport auth: every tool call MUST include ``authorization`` in arguments
(Bearer token). The ChatGPT → relay hop supplies this; Cursor never sees it.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from personal_enigma.cursor_relay.config import load_config_from_env
from personal_enigma.cursor_relay.relay import MCP_TOOLS, RelayService

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "dispatch",
        "description": (
            "Launch a cloud agent against an allowlisted named environment, "
            "repository, and branch. Requires idempotency_key."
        ),
        "inputSchema": {
            "type": "object",
            "required": [
                "authorization",
                "idempotency_key",
                "repository",
                "environment",
                "head_branch",
            ],
            "properties": {
                "authorization": {
                    "type": "string",
                    "description": "Bearer token for authenticated caller identity",
                },
                "idempotency_key": {"type": "string"},
                "repository": {"type": "string"},
                "environment": {"type": "string"},
                "head_branch": {"type": "string"},
                "base_branch": {"type": "string"},
                "model": {"type": "string"},
                "prompt": {"type": "string"},
                "ticket_path": {"type": "string"},
                "ticket_ids": {"type": "array", "items": {"type": "string"}},
                "job_brief": {"type": "object"},
                "auto_create_pr": {"type": "boolean"},
                "name": {"type": "string"},
            },
        },
    },
    {
        "name": "status",
        "description": "Poll run lifecycle / setup / PR linkage (authenticated, read-only authz).",
        "inputSchema": {
            "type": "object",
            "required": ["authorization", "agent_id"],
            "properties": {
                "authorization": {"type": "string"},
                "agent_id": {"type": "string"},
                "run_id": {"type": "string"},
                "head_branch": {"type": "string"},
                "ticket_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "follow_up",
        "description": "Resume the same agent id with a follow-up brief (write-capable).",
        "inputSchema": {
            "type": "object",
            "required": ["authorization", "idempotency_key", "agent_id", "prompt"],
            "properties": {
                "authorization": {"type": "string"},
                "idempotency_key": {"type": "string"},
                "agent_id": {"type": "string"},
                "prompt": {"type": "string"},
                "job_brief": {"type": "object"},
                "head_branch": {"type": "string"},
                "ticket_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "request_review",
        "description": (
            "Request structured review without merging. "
            "Idempotency required when creating a run."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["authorization", "idempotency_key"],
            "properties": {
                "authorization": {"type": "string"},
                "idempotency_key": {"type": "string"},
                "repository": {"type": "string"},
                "environment": {"type": "string"},
                "head_branch": {"type": "string"},
                "base_branch": {"type": "string"},
                "model": {"type": "string"},
                "prompt": {"type": "string"},
                "agent_id": {"type": "string"},
                "create_run": {"type": "boolean"},
                "job_brief": {"type": "object"},
                "ticket_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    {
        "name": "cancel",
        "description": "Cancel an in-flight run (approval-gated).",
        "inputSchema": {
            "type": "object",
            "required": ["authorization", "agent_id", "run_id"],
            "properties": {
                "authorization": {"type": "string"},
                "agent_id": {"type": "string"},
                "run_id": {"type": "string"},
                "head_branch": {"type": "string"},
                "ticket_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
]


class McpStdioServer:
    """JSON-RPC MCP subset over stdio (tools/list + tools/call)."""

    def __init__(self, service: RelayService) -> None:
        self.service = service

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method")
        msg_id = message.get("id")
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "enigma-cursor-relay", "version": "0.1.0"},
                },
            }
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOL_SCHEMAS},
            }
        if method == "tools/call":
            params = message.get("params") or {}
            name = params.get("name")
            arguments = dict(params.get("arguments") or {})
            auth = arguments.pop("authorization", None)
            if name not in MCP_TOOLS:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {name}"},
                }
            handoff = self.service.invoke(str(name), arguments, authorization=auth)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(handoff, indent=2, sort_keys=True),
                        }
                    ],
                    "structuredContent": handoff,
                    "isError": handoff.get("recommended_action", {}).get("kind")
                    == "stop_needs_human"
                    and "Denied" in (handoff.get("recommended_action", {}).get("rationale") or ""),
                },
            }
        if msg_id is None:
            return None
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    def serve_stdio(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            message = json.loads(line)
            response = self.handle(message)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()


def main() -> None:
    config = load_config_from_env()
    service = RelayService(config)
    McpStdioServer(service).serve_stdio()


if __name__ == "__main__":
    main()
