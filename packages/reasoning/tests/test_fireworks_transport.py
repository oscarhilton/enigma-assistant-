"""Tests for Fireworks Chat Completions transport (R-L03)."""

from __future__ import annotations

import io
import json
from email.message import Message
from typing import Any
from urllib.error import HTTPError

import pytest

from personal_enigma.reasoning.fireworks_transport import (
    DEFAULT_FIREWORKS_MODEL,
    DEFAULT_REASONING_EFFORT,
    FireworksChatTransport,
    describe_message_shape,
    fireworks_seed,
)
from personal_enigma.reasoning.structured_output import (
    JudgeV1ParseError,
    judge_v1_response_format,
    parse_judge_v1_output,
)
from personal_enigma.transformation import TransformedContext

_JUDGE_JSON = json.dumps(
    {
        "schema_version": "judge-v1",
        "attention": {
            "decision": "surface",
            "priority": 4,
            "confidence": 0.9,
            "reason_codes": ["USER_COMMITMENT"],
            "evidence_ids": ["rem-brunch-book"],
        },
        "next_action": None,
    }
)


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def _success_payload(content: str) -> bytes:
    return json.dumps(
        {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 180},
        }
    ).encode("utf-8")


def _fake_urlopen_factory(
    response_body: bytes,
    *,
    fail_on_seed: bool = False,
) -> Any:
    calls: list[dict[str, Any]] = []

    def _urlopen(req: Any, timeout: float = 0) -> _FakeResponse:
        body = json.loads(req.data.decode("utf-8"))
        calls.append(body)
        assert "store" not in body
        assert body["response_format"]["type"] == "json_schema"
        assert body["response_format"]["json_schema"]["name"] == "judge_v1_output"
        assert body["reasoning_effort"] == DEFAULT_REASONING_EFFORT
        assert body["messages"][0]["role"] == "system"
        assert "judge-v1" in body["messages"][0]["content"]
        assert req.full_url.endswith("/chat/completions")
        assert body["messages"][1]["content"] == "Return JSON only"
        if fail_on_seed and "seed" in body:
            raise HTTPError(
                req.full_url,
                400,
                "unsupported seed",
                Message(),
                io.BytesIO(b'{"error":{"message":"seed unsupported"}}'),
            )
        if "seed" in body:
            assert body["seed"] == fireworks_seed(checkpoint_id="cp-test", rep=2)
        assert body["max_tokens"] == 512
        return _FakeResponse(response_body)

    _urlopen.calls = calls  # type: ignore[attr-defined]
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
    urlopen = _fake_urlopen_factory(_success_payload(_JUDGE_JSON))
    transport = FireworksChatTransport(
        api_key="test-key",
        urlopen=urlopen,
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
    assert "judge-v1" in result.text


def test_fireworks_transport_retries_without_seed_on_400() -> None:
    urlopen = _fake_urlopen_factory(
        _success_payload(_JUDGE_JSON),
        fail_on_seed=True,
    )
    transport = FireworksChatTransport(api_key="test-key", urlopen=urlopen)
    result = transport.complete(
        prompt="Return JSON only",
        context=TransformedContext(
            summary="Checkpoint snapshot",
            entities=["OBLIGATION_A"],
            metadata={"checkpoint_id": "cp-test", "record_id": "cp-test"},
            may_transmit_remotely=True,
        ),
        rep=2,
    )
    assert result.metadata["status"] == "ok"
    assert urlopen.calls[0]["seed"] == fireworks_seed(checkpoint_id="cp-test", rep=2)
    assert "seed" not in urlopen.calls[1]


def test_fireworks_transport_error_is_not_valid_judge_json() -> None:
    with pytest.raises(JudgeV1ParseError, match="transport error"):
        parse_judge_v1_output("[fireworks transport error: HTTP 401: unauthorized]")


def test_fireworks_transport_model_rejection_is_transport_error() -> None:
    payload = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "name": "Invalid",
                                "reason": "Missing these required fields.",
                            }
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
    ).encode("utf-8")
    transport = FireworksChatTransport(
        api_key="test-key",
        urlopen=_fake_urlopen_factory(payload),
    )
    result = transport.complete(
        prompt="Return JSON only",
        context=TransformedContext(
            summary="Checkpoint snapshot",
            entities=["OBLIGATION_A"],
            metadata={"checkpoint_id": "cp-test", "record_id": "cp-test"},
            may_transmit_remotely=True,
        ),
        rep=2,
    )
    assert result.metadata["status"] == "error"
    assert "model rejection" in result.text


def test_fireworks_transport_prefers_harmony_final_over_invalid_content() -> None:
    invalid = json.dumps({"name": "Invalid", "reason": "placeholder"})
    harmony = (
        "<|channel|>analysis<|message|>thinking..."
        f"<|channel|>final<|message|>{_JUDGE_JSON}"
    )
    payload = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "content": invalid,
                        "reasoning_content": harmony,
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
    ).encode("utf-8")
    transport = FireworksChatTransport(
        api_key="test-key",
        urlopen=_fake_urlopen_factory(payload),
    )
    result = transport.complete(
        prompt="Return JSON only",
        context=TransformedContext(
            summary="Checkpoint snapshot",
            entities=["OBLIGATION_A"],
            metadata={"checkpoint_id": "cp-test", "record_id": "cp-test"},
            may_transmit_remotely=True,
        ),
        rep=2,
    )
    assert result.metadata["status"] == "ok"
    out = parse_judge_v1_output(result.text)
    assert out.attention.decision == "surface"


def test_fireworks_transport_uses_message_parsed_json() -> None:
    parsed = json.loads(_JUDGE_JSON)
    payload = json.dumps(
        {
            "choices": [
                {
                    "message": {"content": None, "parsed": parsed},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
    ).encode("utf-8")
    transport = FireworksChatTransport(
        api_key="test-key",
        urlopen=_fake_urlopen_factory(payload),
    )
    result = transport.complete(
        prompt="Return JSON only",
        context=TransformedContext(
            summary="Checkpoint snapshot",
            entities=["OBLIGATION_A"],
            metadata={"checkpoint_id": "cp-test", "record_id": "cp-test"},
            may_transmit_remotely=True,
        ),
        rep=2,
    )
    assert result.metadata["status"] == "ok"
    out = parse_judge_v1_output(result.text)
    assert out.schema_version == "judge-v1"


def test_fireworks_transport_content_parts_array() -> None:
    payload = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "content": [{"type": "output_text", "text": _JUDGE_JSON}],
                    }
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
    ).encode("utf-8")
    transport = FireworksChatTransport(
        api_key="test-key",
        urlopen=_fake_urlopen_factory(payload),
    )
    result = transport.complete(
        prompt="Return JSON only",
        context=TransformedContext(
            summary="Checkpoint snapshot",
            entities=["OBLIGATION_A"],
            metadata={"checkpoint_id": "cp-test", "record_id": "cp-test"},
            may_transmit_remotely=True,
        ),
        rep=2,
    )
    out = parse_judge_v1_output(result.text)
    assert out.attention.decision == "surface"


def test_fireworks_transport_reasoning_only_analysis_is_parse_error() -> None:
    """Regression: gpt-oss may fill max_tokens with analysis CoT and no final JSON."""
    reasoning_only = (
        "<|channel|>analysis<|message|>"
        "Weighing brunch obligation against calendar conflicts..."
    )
    payload = json.dumps(
        {
            "choices": [
                {
                    "message": {"content": None, "reasoning_content": reasoning_only},
                    "finish_reason": "length",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 512},
        }
    ).encode("utf-8")
    transport = FireworksChatTransport(
        api_key="test-key",
        urlopen=_fake_urlopen_factory(payload),
    )
    result = transport.complete(
        prompt="Return JSON only",
        context=TransformedContext(
            summary="Checkpoint snapshot",
            entities=["OBLIGATION_A"],
            metadata={"checkpoint_id": "cp-test", "record_id": "cp-test"},
            may_transmit_remotely=True,
        ),
        rep=2,
    )
    assert result.metadata["finish_reason"] == "length"
    assert "reasoning_has_final=False" in result.metadata["response_shape"]
    with pytest.raises(JudgeV1ParseError, match="no JSON object found"):
        parse_judge_v1_output(result.text)


def test_describe_message_shape_summarizes_fields() -> None:
    shape = describe_message_shape(
        {
            "content": None,
            "reasoning_content": "<|channel|>analysis<|message|>thinking",
        }
    )
    assert "content_len=0" in shape
    assert "reasoning_has_final=False" in shape


def test_fireworks_transport_network_error() -> None:
    def _fail(_req: Any, timeout: float = 0) -> _FakeResponse:
        raise HTTPError(
            "https://api.fireworks.ai", 503, "unavailable", Message(), io.BytesIO()
        )

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


def test_fireworks_transport_parses_judge_with_trailing_extra_json() -> None:
    """Regression: live responses may include valid judge-v1 plus trailing JSON."""
    trailing = json.dumps({"name": "Invalid", "reason": "placeholder"}, indent=2)
    content = f"{_JUDGE_JSON}\n{trailing}"
    transport = FireworksChatTransport(
        api_key="test-key",
        urlopen=_fake_urlopen_factory(_success_payload(content)),
    )
    result = transport.complete(
        prompt="Return JSON only",
        context=TransformedContext(
            summary="Checkpoint snapshot",
            entities=["OBLIGATION_A"],
            metadata={"checkpoint_id": "cp-test", "record_id": "cp-test"},
            may_transmit_remotely=True,
        ),
        rep=2,
    )
    assert result.metadata["status"] == "ok"
    out = parse_judge_v1_output(result.text)
    assert out.attention.decision == "surface"
