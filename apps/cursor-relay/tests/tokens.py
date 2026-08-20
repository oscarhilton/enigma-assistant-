"""Shared test tokens — never real credentials."""

READER = "test-token-reader"
DISPATCHER = "test-token-dispatcher"
APPROVER = "test-token-approver"
ADMIN = "test-token-admin"


def bearer(token: str) -> str:
    return f"Bearer {token}"
