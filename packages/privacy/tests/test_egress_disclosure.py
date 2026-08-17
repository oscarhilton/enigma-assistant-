"""Disclosure records must contain hashes/metadata only — no raw private payloads."""

from __future__ import annotations

import json

from personal_enigma.privacy.egress import (
    InMemoryDisclosureStore,
    RemoteSafeContext,
    build_audited_egress_gate,
)
from personal_enigma.privacy.remote import RemoteInferenceConfig
from personal_enigma.transformation import TransformedContext


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_disclosure_metadata_only_no_raw_content() -> None:
    secret_summary = "Oscar Hilts must reply to oscar.hilts@example.com"
    ctx = TransformedContext(
        summary=secret_summary,
        entities=["PERSON_A4F91C"],
        metadata={"source_type": "email"},
        may_transmit_remotely=True,
    )
    store = InMemoryDisclosureStore()
    gate = build_audited_egress_gate(
        remote_config=RemoteInferenceConfig(enabled=True),
        disclosure_store=store,
        openai_api_key="test-key",
        openai_urlopen=lambda *_a, **_k: _FakeResponse(
            {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 1},
            }
        ),
    )
    remote_ctx = RemoteSafeContext.from_transformed(
        ctx, provider="openai", model="gpt-4o-mini", prompt="test"
    )
    gate.send(remote_ctx, purpose="reasoning.openai_chat")

    record = store.recent(limit=1)[0]
    assert record.payload_hash
    assert record.payload_field_summary.get("summary_word_count") == len(secret_summary.split())
    assert record.provider == "openai"
    assert record.prompt_tokens == 5
    # Field summary stays counts-only even when the exact payload tab stores the wire body.
    assert secret_summary not in json.dumps(record.payload_field_summary)
    assert "oscar.hilts@example.com" not in json.dumps(record.payload_field_summary)


def test_blocked_disclosure_records_reason_not_payload() -> None:
    store = InMemoryDisclosureStore()
    gate = build_audited_egress_gate(
        remote_config=RemoteInferenceConfig(enabled=False),
        disclosure_store=store,
    )
    gate.send("raw attacker body", purpose="conversation.orchestrate")
    record = store.recent(limit=1)[0]
    assert record.blocked is True
    assert record.block_reason
    assert "attacker" not in record.model_dump_json()


def test_conversation_disclosure_outbound_is_exact_wire_without_secrets() -> None:
    captured: list[bytes] = []

    def _urlopen(req: object, timeout: float = 0) -> _FakeResponse:
        captured.append(getattr(req, "data", b""))
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "type": "function",
                                    "function": {"name": "world.explain", "arguments": "{}"},
                                }
                            ],
                        }
                    }
                ],
                "usage": {},
            }
        )

    store = InMemoryDisclosureStore()
    gate = build_audited_egress_gate(
        remote_config=RemoteInferenceConfig(enabled=True),
        disclosure_store=store,
        fireworks_api_key="fw-secret-key",
        fireworks_urlopen=_urlopen,
    )
    remote_ctx = RemoteSafeContext.for_conversation_orchestrator(
        user_message="Why do I need to do this?",
        context_summary={
            "current_subject_id": "item-obligation_token_audit",
            "current_subject_kind": "next_action",
            "simulated_time": "2026-01-19T10:00:00+00:00",
            "attention_count": 1,
        },
        tools=[{"type": "function", "function": {"name": "world.explain"}}],
        model="accounts/fireworks/models/gpt-oss-120b",
        provider="fireworks",
    )
    gate.send(remote_ctx, purpose="conversation.orchestrate")
    record = store.recent(limit=1)[0]
    wire = json.loads(captured[0].decode("utf-8"))
    assert record.outbound_payload["messages"] == wire["messages"]
    assert record.outbound_payload["tools"] == wire["tools"]
    assert "fw-secret-key" not in record.model_dump_json()
    user_content = json.loads(record.outbound_payload["messages"][1]["content"])
    assert user_content["user_message"] == "Why do I need to do this?"
    assert "raw email bodies" in record.excluded
    dumped = record.model_dump_json()
    assert "@" not in dumped
