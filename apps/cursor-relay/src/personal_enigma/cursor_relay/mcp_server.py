"""Minimal MCP stdio server exposing relay tools.

Secure MCP Tunnel pilot: caller identity is derived server-side from
``RELAY_TUNNEL_CALLER`` and injected into ``RelayService``. Public tool
schemas and model-supplied arguments never carry bearer tokens or credentials.
Multi-user / public deployment requires MCP OAuth (not model-visible secrets).
"""

from __future__ import annotations

import json
import sys
from typing import Any

from personal_enigma.cursor_relay.auth import (
    AuthError,
    reject_model_supplied_secrets,
    resolve_tunnel_caller,
)
from personal_enigma.cursor_relay.config import load_config_from_env
from personal_enigma.cursor_relay.handoff import denial_handoff, strip_secrets
from personal_enigma.cursor_relay.relay import MCP_TOOLS, RelayService

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "dispatch",
        "description": (
            "Launch a cloud agent against an allowlisted named environment, "
            "repository, and branch — or an existing GitHub PR via pr_url. "
            "Requires idempotency_key. "
            "Caller identity is server-side (Secure MCP Tunnel); do not pass secrets."
        ),
        "inputSchema": {
            "type": "object",
            "required": [
                "idempotency_key",
                "repository",
                "environment",
                "head_branch",
            ],
            "properties": {
                "idempotency_key": {"type": "string"},
                "repository": {"type": "string"},
                "environment": {"type": "string"},
                "head_branch": {"type": "string"},
                "base_branch": {"type": "string"},
                "model": {
                    "type": "string",
                    "description": (
                        "Optional explicit model id. Omit for Cursor default/green. "
                        "Premium models require model_escalation_reason."
                    ),
                },
                "model_escalation_reason": {
                    "type": "string",
                    "description": (
                        "Required when model is premium (composer-2.5*, grok, gpt-5*, "
                        "thinking). Concise escalation justification (8-240 chars)."
                    ),
                },
                "prompt": {"type": "string"},
                "ticket_path": {"type": "string"},
                "ticket_ids": {"type": "array", "items": {"type": "string"}},
                "job_brief": {"type": "object"},
                "auto_create_pr": {"type": "boolean"},
                "pr_url": {
                    "type": "string",
                    "description": (
                        "Existing GitHub PR URL. Uses native repos[].prUrl + "
                        "workOnCurrentBranch=true (no named-env busboy branch)."
                    ),
                },
                "name": {"type": "string"},
            },
        },
    },
    {
        "name": "status",
        "description": (
            "Poll run lifecycle / setup / PR linkage "
            "(server-side authenticated; read-only authz)."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["agent_id"],
            "properties": {
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
            "required": ["idempotency_key", "agent_id", "prompt"],
            "properties": {
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
            "required": ["idempotency_key"],
            "properties": {
                "idempotency_key": {"type": "string"},
                "repository": {"type": "string"},
                "environment": {"type": "string"},
                "head_branch": {"type": "string"},
                "base_branch": {"type": "string"},
                "model": {
                    "type": "string",
                    "description": (
                        "Optional explicit model id. Omit for Cursor default/green. "
                        "Premium models require model_escalation_reason."
                    ),
                },
                "model_escalation_reason": {
                    "type": "string",
                    "description": (
                        "Required when model is premium (composer-2.5*, grok, gpt-5*, "
                        "thinking). Concise escalation justification (8-240 chars)."
                    ),
                },
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
            "required": ["agent_id", "run_id"],
            "properties": {
                "agent_id": {"type": "string"},
                "run_id": {"type": "string"},
                "head_branch": {"type": "string"},
                "ticket_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
]


def _schema_mentions_secrets(tools: list[dict[str, Any]]) -> list[str]:
    """Collect forbidden credential property names found in public schemas."""

    from personal_enigma.cursor_relay.auth import MODEL_SUPPLIED_SECRET_KEYS

    hits: list[str] = []
    for tool in tools:
        props = (tool.get("inputSchema") or {}).get("properties") or {}
        required = (tool.get("inputSchema") or {}).get("required") or []
        for key in list(props) + list(required):
            if str(key).lower() in MODEL_SUPPLIED_SECRET_KEYS:
                hits.append(f"{tool.get('name')}:{key}")
        blob = json.dumps(tool).lower()
        for banned in ("bearer", "api_key", "cursor_api_key", "relay_auth"):
            if banned in blob:
                hits.append(f"{tool.get('name')}:description_or_schema:{banned}")
    return hits


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
            if name not in MCP_TOOLS:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {name}"},
                }
            try:
                reject_model_supplied_secrets(arguments)
                caller = resolve_tunnel_caller(self.service.config)
            except AuthError as exc:
                handoff = strip_secrets(
                    denial_handoff(tool=str(name), reason=str(exc), code=exc.code)
                )
                self.service.audit.emit(
                    tool=str(name),
                    caller_id="anonymous",
                    decision="deny",
                    detail=str(exc),
                    extra={"code": exc.code},
                )
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
                        "isError": True,
                    },
                }
            handoff = self.service.invoke(str(name), arguments, caller=caller)
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
