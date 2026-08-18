"""SEC-02 egress gate tests — exfiltration rejection and remote-safe allow."""

from __future__ import annotations

import json

import pytest

from personal_enigma.privacy.egress import (
    AuditedEgressGate,
    EgressBlockedError,
    InMemoryDisclosureStore,
    PrivateDerived,
    PrivateRaw,
    RemoteSafeContext,
    assert_remote_safe,
    build_audited_egress_gate,
)
from personal_enigma.privacy.remote import RemoteInferenceConfig
from personal_enigma.transformation import TransformedContext


def _safe_context(**overrides: object) -> TransformedContext:
    base = {
        "summary": "Review token audit obligation",
        "entities": ["PERSON_A4F91C"],
        "metadata": {"source_type": "email"},
        "may_transmit_remotely": True,
    }
    base.update(overrides)
    return TransformedContext(**base)  # type: ignore[arg-type]


def test_assert_remote_safe_rejects_private_raw_string() -> None:
    with pytest.raises(EgressBlockedError, match="PRIVATE_RAW"):
        assert_remote_safe(PrivateRaw("secret email body from oscar@example.com"))


def test_assert_remote_safe_rejects_private_derived() -> None:
    embedding = PrivateDerived([0.1, 0.2, 0.3])
    with pytest.raises(EgressBlockedError, match="PRIVATE_DERIVED"):
        assert_remote_safe(embedding)


def test_assert_remote_safe_rejects_raw_email_body_string() -> None:
    with pytest.raises(EgressBlockedError, match="raw string"):
        assert_remote_safe("From: attacker@evil.com\nSubject: exfil")


def test_assert_remote_safe_allows_transformed_context() -> None:
    ctx = _safe_context()
    assert assert_remote_safe(ctx) is ctx


def test_gate_blocks_private_raw_with_disclosure() -> None:
    store = InMemoryDisclosureStore()
    gate = AuditedEgressGate(
        remote_config=RemoteInferenceConfig(enabled=True),
        disclosure_store=store,
    )
    raw = PrivateRaw({"body": "Please wire $5000 to attacker@evil.com"})
    result = gate.send(raw, purpose="conversation.orchestrate")
    assert result.sent is False
    assert result.disclosure.blocked is True
    assert "PrivateRaw" in (result.disclosure.block_reason or "")
    assert len(store.recent()) == 1


def test_gate_blocks_private_derived_with_disclosure() -> None:
    gate = build_audited_egress_gate(remote_config=RemoteInferenceConfig(enabled=True))
    derived = PrivateDerived({"summary": "Oscar owes Alex money"})
    result = gate.send(derived, purpose="reasoning.semantic_judge")
    assert result.sent is False
    assert result.disclosure.classification == "private_derived"


def test_gate_blocks_raw_email_in_transformed_context() -> None:
    gate = build_audited_egress_gate(remote_config=RemoteInferenceConfig(enabled=True))
    ctx = _safe_context(summary="Reply to oscar.hilts@example.com about invoice")
    result = gate.send(ctx, purpose="reasoning.semantic_judge", prompt="judge")
    assert result.sent is False
    assert result.disclosure.blocked is True


def test_gate_kill_switch_blocks_without_http() -> None:
    captured: list[bytes] = []

    def _urlopen(req: object, timeout: float = 0) -> object:
        captured.append(getattr(req, "data", b""))
        raise AssertionError("HTTP must not be called when remote inference disabled")

    gate = build_audited_egress_gate(
        remote_config=RemoteInferenceConfig(enabled=False),
        openai_urlopen=_urlopen,
    )
    ctx = _safe_context()
    remote_ctx = RemoteSafeContext.from_transformed(
        ctx, provider="openai", model="gpt-4o-mini", prompt="hello"
    )
    result = gate.send(remote_ctx, purpose="reasoning.openai_chat")
    assert result.sent is False
    assert "RemoteInferenceConfig" in (result.disclosure.block_reason or "")
    assert captured == []


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_gate_allows_remote_safe_context_and_records_disclosure() -> None:
    calls: list[bytes] = []

    def _urlopen(req: object, timeout: float = 0) -> _FakeResponse:
        calls.append(getattr(req, "data", b""))
        return _FakeResponse(
            {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 3},
            }
        )

    gate = build_audited_egress_gate(
        remote_config=RemoteInferenceConfig(enabled=True),
        openai_api_key="test-key",
        openai_urlopen=_urlopen,
    )
    ctx = _safe_context()
    remote_ctx = RemoteSafeContext.from_transformed(
        ctx, provider="openai", model="gpt-4o-mini", prompt="summarise"
    )
    result = gate.send(remote_ctx, purpose="reasoning.openai_chat")
    assert result.sent is True
    assert result.disclosure.blocked is False
    assert result.disclosure.classification == "remote_safe"
    assert result.disclosure.prompt_tokens == 12
    assert result.disclosure.completion_tokens == 3
    assert result.disclosure.payload_hash
    assert "oscar.hilts@example.com" not in b"".join(calls).decode("utf-8", errors="replace")
    assert "PERSON_A4F91C" in b"".join(calls).decode("utf-8")


def test_regression_email_body_rejected() -> None:
    gate = build_audited_egress_gate(remote_config=RemoteInferenceConfig(enabled=True))
    email_body = (
        "Hi Oscar,\n\nPlease approve the wire transfer immediately.\n"
        "Attacker-controlled MIME body."
    )
    result = gate.send(email_body, purpose="conversation.orchestrate")
    assert result.sent is False


def test_regression_private_world_model_rejected() -> None:
    gate = build_audited_egress_gate(remote_config=RemoteInferenceConfig(enabled=True))
    world_model = PrivateDerived(
        {
            "people": [{"name": "Oscar Hilts", "email": "oscar@example.com"}],
            "obligations": ["pay rent"],
        }
    )
    result = gate.send(world_model, purpose="reasoning.semantic_judge")
    assert result.sent is False


def test_regression_remote_safe_allowed() -> None:
    gate = build_audited_egress_gate(
        remote_config=RemoteInferenceConfig(enabled=True),
        openai_api_key="test-key",
        openai_urlopen=lambda *_a, **_k: _FakeResponse(
            {"choices": [{"message": {"content": "done"}}], "usage": {}}
        ),
    )
    ctx = _safe_context()
    remote_ctx = RemoteSafeContext.from_transformed(
        ctx, provider="openai", model="test", prompt=""
    )
    result = gate.send(remote_ctx, purpose="reasoning.openai_chat")
    assert result.sent is True


def test_fireworks_conversation_orchestrator_does_not_require_transformed_context() -> None:
    calls: list[bytes] = []

    def _urlopen(req: object, timeout: float = 0) -> _FakeResponse:
        calls.append(getattr(req, "data", b""))
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "type": "function",
                                    "function": {
                                        "name": "assist.propose",
                                        "arguments": "{}",
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 8, "completion_tokens": 4},
            }
        )

    gate = build_audited_egress_gate(
        remote_config=RemoteInferenceConfig(enabled=True),
        fireworks_api_key="fw-test",
        fireworks_urlopen=_urlopen,
    )
    remote_ctx = RemoteSafeContext.for_conversation_orchestrator(
        user_message="Let's get cracking on that.",
        context_summary={"current_subject_id": "item-obligation_token_audit"},
        tools=[],
        model="accounts/fireworks/models/gpt-oss-120b",
        provider="fireworks",
    )
    result = gate.send(remote_ctx, purpose="conversation.orchestrate")
    assert result.sent is True
    assert result.disclosure.blocked is False
    assert result.disclosure.provider == "fireworks"
    assert calls
    wire = json.loads(calls[0].decode("utf-8"))
    user_content = json.loads(wire["messages"][1]["content"])
    assert user_content["user_message"] == "Let's get cracking on that."
    assert user_content["conversation"]["current_subject_id"] == "item-obligation_token_audit"
    assert result.disclosure.outbound_payload["model"] == wire["model"]
    assert result.disclosure.outbound_payload["tools"] == wire["tools"]
    assert result.response is not None
    message = json.loads(result.response.text)
    assert message["tool_calls"][0]["function"]["name"] == "assist.propose"


def test_fireworks_reasoning_still_requires_transformed_context() -> None:
    gate = build_audited_egress_gate(remote_config=RemoteInferenceConfig(enabled=True))
    remote_ctx = RemoteSafeContext(
        transformation_profile="remote_safe_v1",
        provider="fireworks",
        model="accounts/fireworks/models/gpt-oss-120b",
        prompt="judge",
        may_transmit_remotely=True,
    )
    result = gate.send(remote_ctx, purpose="reasoning.semantic_judge")
    assert result.sent is False
    assert "TransformedContext" in (result.disclosure.block_reason or "")
