"""User-inspectable egress disclosure records — hashes, summary, and exact remote-safe payload."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

CONVERSATION_EGRESS_INCLUDED: tuple[str, ...] = (
    "current user message",
    "simulated time",
    "attention count",
    "permitted tool schemas",
)
CONVERSATION_EGRESS_EXCLUDED: tuple[str, ...] = (
    "PRIVATE_RAW",
    "raw email bodies",
    "calendar event descriptions",
    "contact identities",
    "source records",
    "attachments",
    "private memory",
)

_SECRET_KEY_FRAGMENTS = ("authorization", "api_key", "api-key", "x-api-key", "bearer", "secret")


def redact_transport_secrets(value: Any) -> Any:
    """Strip transport credentials from a payload copy. Never redact tool/subject ids."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            lowered = str(key).lower().replace("_", "-")
            if any(fragment in lowered for fragment in _SECRET_KEY_FRAGMENTS):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = redact_transport_secrets(nested)
        return redacted
    if isinstance(value, list):
        return [redact_transport_secrets(item) for item in value]
    return value


def tool_names_from_wire(wire_body: dict[str, Any] | None) -> list[str]:
    """Tool names supplied to the model — derived from the wire body, not a parallel list."""
    if not isinstance(wire_body, dict):
        return []
    names: list[str] = []
    for tool in wire_body.get("tools") or []:
        if not isinstance(tool, dict):
            continue
        name = (tool.get("function") or {}).get("name")
        if name:
            names.append(str(name))
    return names


class EgressDisclosure(BaseModel):
    """What crossed the egress boundary — exact remote-safe payload, never PRIVATE_RAW."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    correlation_id: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(tz=UTC).isoformat(),
    )
    purpose: str
    provider: str
    model: str
    transformation_profile: str
    payload_field_summary: dict[str, Any] = Field(default_factory=dict)
    payload_hash: str
    byte_count: int
    blocked: bool = False
    block_reason: str | None = None
    classification: str = "remote_safe"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    outbound_payload: dict[str, Any] = Field(default_factory=dict)
    provider_response: dict[str, Any] | None = None
    transport_endpoint: str | None = None
    included: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    denied_capabilities: list[str] = Field(default_factory=list)
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)
    enigma_actions: list[dict[str, Any]] = Field(default_factory=list)
