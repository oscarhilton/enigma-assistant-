"""Caller identity for the relay — never from model-supplied MCP arguments.

Secure MCP Tunnel pilot: identity is fixed on the relay host
(``RELAY_TUNNEL_CALLER``) and injected internally. Multi-user / public
deployments require MCP OAuth (not model-visible bearer tokens).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from personal_enigma.cursor_relay.config import CallerRecord, RelayConfig

# Top-level MCP argument keys that must never appear in public tool schemas
# or be accepted from the model. ``job_brief.authorization`` (policy flags)
# is nested and is not in this set.
MODEL_SUPPLIED_SECRET_KEYS = frozenset(
    {
        "authorization",
        "bearer",
        "token",
        "api_key",
        "cursor_api_key",
        "relay_auth_token",
        "relay_auth_tokens",
        "chatgpt_api_key",
        "chatgpt_session",
        "openai_chatgpt_token",
        "access_token",
        "secret",
        "password",
    }
)


class AuthError(Exception):
    """Caller failed authentication at the trusted transport boundary."""

    def __init__(self, message: str, *, code: str = "unauthenticated") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AuthenticatedCaller:
    caller_id: str
    roles: frozenset[str]
    display_name: str | None = None

    def has_role(self, role: str) -> bool:
        return role in self.roles or "admin" in self.roles


def caller_from_record(record: CallerRecord) -> AuthenticatedCaller:
    return AuthenticatedCaller(
        caller_id=record.caller_id,
        roles=record.roles,
        display_name=record.display_name,
    )


def resolve_tunnel_caller(config: RelayConfig) -> AuthenticatedCaller:
    """Fixed single-user identity from relay-host config (Secure MCP Tunnel).

    Missing configuration is anonymous at the trusted transport boundary.
    """

    if config.tunnel_caller is None:
        raise AuthError(
            "Secure MCP Tunnel caller not configured (RELAY_TUNNEL_CALLER)",
            code="unauthenticated",
        )
    return caller_from_record(config.tunnel_caller)


def find_model_supplied_secret_keys(arguments: dict[str, Any]) -> list[str]:
    """Return top-level argument keys that look like credentials."""

    found: list[str] = []
    for key in arguments:
        if str(key).lower() in MODEL_SUPPLIED_SECRET_KEYS:
            found.append(str(key))
    return sorted(found)


def reject_model_supplied_secrets(arguments: dict[str, Any]) -> None:
    """Fail closed if the model attempted to pass credentials as tool args."""

    found = find_model_supplied_secret_keys(arguments)
    if found:
        raise AuthError(
            "Model-supplied credential arguments are not accepted "
            f"(keys={found}); identity is server-side only",
            code="model_supplied_secret",
        )
