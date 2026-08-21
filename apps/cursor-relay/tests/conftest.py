"""Shared fixtures for cursor-relay tests. Never use real CURSOR_API_KEY values."""

from __future__ import annotations

import pytest

from personal_enigma.cursor_relay.config import CallerRecord, RelayConfig
from personal_enigma.cursor_relay.cursor_client import MockCursorClient
from personal_enigma.cursor_relay.relay import RelayService


@pytest.fixture
def relay_config() -> RelayConfig:
    # Tunnel caller present for MCP path tests; role-matrix tests pass caller= explicitly.
    return RelayConfig(
        cursor_api_key=None,  # mock client — no real key
        tunnel_caller=CallerRecord(
            "tunnel-pilot",
            frozenset({"admin"}),
            display_name="Secure MCP Tunnel pilot",
        ),
    )


@pytest.fixture
def mock_cursor() -> MockCursorClient:
    return MockCursorClient()


@pytest.fixture
def service(relay_config: RelayConfig, mock_cursor: MockCursorClient) -> RelayService:
    return RelayService(relay_config, cursor=mock_cursor)
