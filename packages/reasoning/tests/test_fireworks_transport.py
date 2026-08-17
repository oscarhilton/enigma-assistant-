"""Tests for Fireworks Chat Completions transport (R-L03)."""

from __future__ import annotations

import io
import json
from typing import Any
from urllib.error import HTTPError

from personal_enigma.reasoning.fireworks_transport import (
    DEFAULT_FIREWORKS_MODEL,
    FireworksChatTransport,
    fireworks_seed,
)
from personal_enigma.transformation import TransformedContext

_LLM_RESPONSE = json.dumps(
    {
        "attention": {
            "item_id": "item-1",
            "behaviour": "surface",
            "priority": 4,
        },
        "next_action": {
            "title": "Reply to Elena",
            "estimated_minutes": 5,
            "effort": "light",
            "why_this_now": "Weekend plans pending",
        },
    }
).encode("utf-8")


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def _fake_urlopen_factory(response_body: bytes) -> Any:
    def _urlopen(req: Any, timeout: float = 0) -> _FakeResponse:
        body = json.loads(req.data.decode("utf-8"))
        assert "store" not in body
        assert body["seed"] == fireworks_seed(checkpoint_id="cp-test", rep=2)
        assert body["max_tokens"] == 512
        assert req.full_url.endswith("/chat/completions")
        return _FakeResponse(response_body)

    return _urlopen


def test_fireworks_seed_is_deterministic() -> None:
    assert fireworks_seed(checkpoint_id="cp-2026-01-21T13:30", rep=1) == fireworks_seed(
        checkpoint_id="cp-2026-01-21T13:30", rep=1
    )
    assert fireworks_seed(checkpoint_id="cp-2026-01-21T13:30", rep=1) != fireworks_seed(
        checkpoint_id="cp-2026-01-21T13:30", rep=2
    )


def test_fireworks_transport_no_key_stays_local() -> None:
    transport = FireworksChatTransport(api_key="")
    result = transport.complete(
        prompt="Judge this checkpoint",
        context=TransformedContext(
            summary="Parents brunch conflict",
            entities=["OBLIGATION_BRUNCH"],
            metadata={"checkpoint_id": "cp-test", "record_id": "cp-test"},
            may_transmit_remotely=True,
        ),
        rep=0,
    )
    assert result.metadata["left_machine"] == "false"
    assert result.metadata["provider"] == "fireworks"
    assert "no api key" in result.text.lower() or "stub" in result.text.lower()


def test_fireworks_transport_mock_no_network() -> None:
    payload = json.dumps(
        {
            "choices": [{"message": {"content": _LLM_RESPONSE.decode("utf-8")}}],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 180},
        }
    ).encode("utf-8")
    transport = FireworksChatTransport(
        api_key="test-key",
        urlopen=_fake_urlopen_factory(payload),
    )
    result = transport.complete(
        model=DEFAULT_FIREWORKS_MODEL,
        prompt="Return JSON only",
        context=TransformedContext(
            summary="Checkpoint snapshot",
            entities=["OBLIGATION_A"],
            metadata={"checkpoint_id": "cp-test", "record_id": "cp-test"},
            may_transmit_remotely=True,
        ),
        rep=2,
    )
    assert result.metadata["left_machine"] == "true"
    assert result.metadata["provider"] == "fireworks"
    assert result.usage is not None
    assert result.usage.prompt_tokens == 1200
    assert result.usage.completion_tokens == 180
    assert "Reply to Elena" in result.text


def test_fireworks_transport_network_error() -> None:
    def _fail(_req: Any, timeout: float = 0) -> _FakeResponse:
        raise HTTPError("https://api.fireworks.ai", 503, "unavailable", hdrs=None, fp=io.BytesIO())

    transport = FireworksChatTransport(api_key="test-key", urlopen=_fail)
    result = transport.complete(
        prompt="x",
        context=TransformedContext(
            summary="y",
            entities=[],
            metadata={"checkpoint_id": "cp-err"},
            may_transmit_remotely=True,
        ),
    )
    assert result.metadata["status"] == "error"
    assert result.metadata["left_machine"] == "true"
