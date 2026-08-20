"""Shared fixtures for cursor-relay tests. Never use real CURSOR_API_KEY values."""

from __future__ import annotations

import pytest
from tokens import ADMIN, APPROVER, DISPATCHER, READER

from personal_enigma.cursor_relay.config import CallerRecord, RelayConfig
from personal_enigma.cursor_relay.cursor_client import MockCursorClient
from personal_enigma.cursor_relay.relay import RelayService


@pytest.fixture
def relay_config() -> RelayConfig:
    return RelayConfig(
        cursor_api_key=None,  # mock client — no real key
        caller_tokens={
            READER: CallerRecord("chatgpt-reader", frozenset({"reader"})),
            DISPATCHER: CallerRecord("chatgpt-dispatcher", frozenset({"dispatcher", "reader"})),
            APPROVER: CallerRecord(
                "chatgpt-approver", frozenset({"approver", "dispatcher", "reader"})
            ),
            ADMIN: CallerRecord("chatgpt-admin", frozenset({"admin"})),
        },
    )


@pytest.fixture
def mock_cursor() -> MockCursorClient:
    return MockCursorClient()


@pytest.fixture
def service(relay_config: RelayConfig, mock_cursor: MockCursorClient) -> RelayService:
    return RelayService(relay_config, cursor=mock_cursor)
