"""Shared test callers — never real credentials; never passed via MCP args."""

from __future__ import annotations

from personal_enigma.cursor_relay.auth import AuthenticatedCaller

READER_CALLER = AuthenticatedCaller("chatgpt-reader", frozenset({"reader"}))
DISPATCHER_CALLER = AuthenticatedCaller(
    "chatgpt-dispatcher", frozenset({"dispatcher", "reader"})
)
APPROVER_CALLER = AuthenticatedCaller(
    "chatgpt-approver", frozenset({"approver", "dispatcher", "reader"})
)
ADMIN_CALLER = AuthenticatedCaller("chatgpt-admin", frozenset({"admin"}))
