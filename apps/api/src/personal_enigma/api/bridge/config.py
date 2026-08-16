"""Bridge token install + client config stubs (ticket M07 / ADR-002).

Core generates the local bearer secret at install time. The macOS Apple Bridge
reads the same secret from Keychain (service/account below) or from
``ENIGMA_BRIDGE_TOKEN`` during development and tests.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

BRIDGE_KEYCHAIN_SERVICE = "com.personal-enigma.apple-bridge"
BRIDGE_KEYCHAIN_ACCOUNT = "bridge-bearer-token"
DEFAULT_BRIDGE_BASE_URL = "http://127.0.0.1:8765"


def generate_bridge_token(*, nbytes: int = 32) -> str:
    """Generate a high-entropy bearer token for the local Apple Bridge."""
    return secrets.token_urlsafe(nbytes)


@dataclass(frozen=True, slots=True)
class BridgeTokenInstallPlan:
    """Metadata describing how Core should persist the bridge token.

    Actual Keychain writes happen on macOS (bridge companion / installer). This
    stub records the intended Keychain coordinates and the token Core generated.
    """

    token: str
    keychain_service: str = BRIDGE_KEYCHAIN_SERVICE
    keychain_account: str = BRIDGE_KEYCHAIN_ACCOUNT


@dataclass(frozen=True, slots=True)
class BridgeClientConfig:
    """Config passed to ``AppleBridgeClient`` from Enigma Core settings."""

    base_url: str = DEFAULT_BRIDGE_BASE_URL
    token: str | None = None
    unix_socket: str | None = None


def plan_bridge_token_install(token: str | None = None) -> BridgeTokenInstallPlan:
    """Create an install plan; generates a token when one is not supplied."""
    return BridgeTokenInstallPlan(token=token or generate_bridge_token())


def bridge_client_config_from_settings(
    *,
    token: str | None,
    base_url: str = DEFAULT_BRIDGE_BASE_URL,
    unix_socket: str | None = None,
) -> BridgeClientConfig:
    """Map persisted settings into client configuration (no network I/O)."""
    return BridgeClientConfig(base_url=base_url, token=token, unix_socket=unix_socket)
