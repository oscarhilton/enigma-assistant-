"""Single-instance pilot guard for in-memory stores."""

from __future__ import annotations

import pytest

from personal_enigma.cursor_relay.config import load_config_from_env

_TUNNEL = '{"caller_id":"pilot","roles":["admin"]}'


def test_multi_instance_without_shared_store_fails_closed() -> None:
    with pytest.raises(ValueError, match="RELAY_SHARED_STORE_URL"):
        load_config_from_env(
            {
                "RELAY_SINGLE_INSTANCE": "0",
                "RELAY_TUNNEL_CALLER": _TUNNEL,
            }
        )


def test_multi_instance_with_shared_store_ok() -> None:
    cfg = load_config_from_env(
        {
            "RELAY_SINGLE_INSTANCE": "0",
            "RELAY_SHARED_STORE_URL": "redis://localhost:6379/0",
            "RELAY_TUNNEL_CALLER": _TUNNEL,
        }
    )
    assert cfg.single_instance is False
    assert cfg.shared_store_url == "redis://localhost:6379/0"


def test_default_single_instance() -> None:
    cfg = load_config_from_env({"RELAY_TUNNEL_CALLER": _TUNNEL})
    assert cfg.single_instance is True
    assert cfg.tunnel_caller is not None
    assert cfg.tunnel_caller.caller_id == "pilot"
