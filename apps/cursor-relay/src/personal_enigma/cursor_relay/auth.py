"""Authenticate every MCP tool invocation — never anonymous."""

from __future__ import annotations

from dataclasses import dataclass

from personal_enigma.cursor_relay.config import CallerRecord, RelayConfig


class AuthError(Exception):
    """Caller failed authentication."""

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


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def authenticate(config: RelayConfig, authorization: str | None) -> AuthenticatedCaller:
    """Resolve bearer token to a caller identity.

    Anonymous (missing/invalid token) always raises — including for ``status``.
    """

    token = extract_bearer_token(authorization)
    if token is None:
        raise AuthError("Missing or invalid Authorization bearer token", code="unauthenticated")
    record: CallerRecord | None = config.caller_tokens.get(token)
    if record is None:
        raise AuthError("Unknown caller token", code="unauthenticated")
    return AuthenticatedCaller(
        caller_id=record.caller_id,
        roles=record.roles,
        display_name=record.display_name,
    )
