"""C09 live egress is one path: Fireworks transport, audit, and disclosure UI facts."""

from __future__ import annotations

import json
from typing import Any

from personal_enigma.api.conversation_context import ConversationContext
from personal_enigma.api.demo_assist import SyntheticDemoServices
from personal_enigma.api.demo_orchestrator import EgressConversationLLM, run_orchestrator_turn
from personal_enigma.api.demo_projection import project_checkpoint
from personal_enigma.api.demo_tools import (
    ALLOWED_TOOL_NAMES,
    DENIED_REMOTE_CAPABILITIES,
    DemoToolSession,
    tool_schemas,
)
from personal_enigma.privacy.egress import (
    InMemoryDisclosureStore,
    build_audited_egress_gate,
    set_audited_egress_gate,
    tool_names_from_wire,
)
from personal_enigma.privacy.remote import RemoteInferenceConfig

TOKEN_ID = "item-obligation_token_audit"
JAN19 = "cp-2026-01-19T10:00"
FIREWORKS_MODEL = "accounts/fireworks/models/gpt-oss-120b"
LEGACY_TOOL_NAMES = {
    "get_attention_state",
    "get_availability",
    "get_recent_sources",
    "propose_assist",
    "get_qualification_debug",
}


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _tool_session() -> DemoToolSession:
    state = project_checkpoint(JAN19).state
    context = ConversationContext(
        current_subject_id=TOKEN_ID,
        current_subject_kind="next_action",
        current_attention_item_id=TOKEN_ID,
        current_next_action_id="next-item-obligation_token_audit",
    )
    return DemoToolSession(
        state=state,
        context=context,
        checkpoint_id=JAN19,
        prior_state=None,
        at=state.simulated_time,
        conversation=[],
        synthetic_services=SyntheticDemoServices(),
    )


def _world_explain_payload() -> dict[str, object]:
    return {
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
        "usage": {"prompt_tokens": 40, "completion_tokens": 8},
    }


def test_provider_identity_transport_audit_and_disclosure_are_one_fact() -> None:
    captured: list[Any] = []

    def _urlopen(req: object, timeout: float = 0) -> _FakeResponse:
        captured.append(req)
        return _FakeResponse(_world_explain_payload())

    store = InMemoryDisclosureStore()
    gate = build_audited_egress_gate(
        remote_config=RemoteInferenceConfig(enabled=True),
        disclosure_store=store,
        fireworks_api_key="fw-test",
        fireworks_urlopen=_urlopen,
    )
    set_audited_egress_gate(gate)
    try:
        llm = EgressConversationLLM(
            provider="fireworks",
            api_key="fw-test",
            model=FIREWORKS_MODEL,
            fallback_to_oracle=False,
            gate=gate,
        )
        turn = run_orchestrator_turn(
            user_message="Why do I need to do this?",
            session=_tool_session(),
            llm=llm,
            correlation_id="corr-123",
        )
    finally:
        set_audited_egress_gate(None)

    assert captured, "expected Fireworks HTTP"
    req = captured[0]
    url = str(getattr(req, "full_url", "") or getattr(req, "get_full_url", lambda: "")())
    assert "fireworks.ai" in url
    wire = json.loads(getattr(req, "data", b"{}").decode("utf-8"))
    assert wire["model"] == FIREWORKS_MODEL
    auth = getattr(req, "headers", {}).get("Authorization") or getattr(req, "headers", {}).get(
        "authorization"
    )
    assert auth is None or "fw-test" in str(auth)

    rows = store.recent(limit=1)
    assert rows
    disclosure = rows[0]
    assert disclosure.provider == "fireworks"
    assert disclosure.model == FIREWORKS_MODEL
    assert disclosure.transport_endpoint is not None
    assert "fireworks.ai" in disclosure.transport_endpoint
    assert disclosure.outbound_payload["model"] == wire["model"]
    assert "fw-test" not in json.dumps(disclosure.model_dump(mode="json"))

    trace = turn.llm_trace
    assert trace is not None
    assert trace.disclosure is not None
    assert trace.disclosure["provider"] == disclosure.provider == "fireworks"


def test_tool_registry_is_one_fact_derived_from_wire() -> None:
    captured: list[bytes] = []

    def _urlopen(req: object, timeout: float = 0) -> _FakeResponse:
        captured.append(getattr(req, "data", b""))
        return _FakeResponse(_world_explain_payload())

    store = InMemoryDisclosureStore()
    gate = build_audited_egress_gate(
        remote_config=RemoteInferenceConfig(enabled=True),
        disclosure_store=store,
        fireworks_api_key="fw-test",
        fireworks_urlopen=_urlopen,
    )
    llm = EgressConversationLLM(
        provider="fireworks",
        api_key="fw-test",
        model=FIREWORKS_MODEL,
        fallback_to_oracle=False,
        gate=gate,
    )
    run_orchestrator_turn(
        user_message="Why do I need to do this?",
        session=_tool_session(),
        llm=llm,
        correlation_id="corr-123",
    )

    wire = json.loads(captured[0].decode("utf-8"))
    schema_names = {
        str((row.get("function") or {}).get("name"))
        for row in tool_schemas()
        if isinstance(row, dict)
    }
    wire_names = set(tool_names_from_wire(wire))
    disclosure_names = set(tool_names_from_wire(store.recent(limit=1)[0].outbound_payload))
    summary_names = set(store.recent(limit=1)[0].payload_field_summary.get("tool_names") or [])

    assert schema_names == set(ALLOWED_TOOL_NAMES)
    assert wire_names == schema_names == disclosure_names == summary_names
    assert wire_names.isdisjoint(LEGACY_TOOL_NAMES)
    assert set(store.recent(limit=1)[0].denied_capabilities) == set(DENIED_REMOTE_CAPABILITIES)


def test_correlation_id_threads_user_turn_payload_tools_and_response() -> None:
    def _urlopen(req: object, timeout: float = 0) -> _FakeResponse:
        return _FakeResponse(_world_explain_payload())

    store = InMemoryDisclosureStore()
    gate = build_audited_egress_gate(
        remote_config=RemoteInferenceConfig(enabled=True),
        disclosure_store=store,
        fireworks_api_key="fw-test",
        fireworks_urlopen=_urlopen,
    )
    llm = EgressConversationLLM(
        provider="fireworks",
        api_key="fw-test",
        model=FIREWORKS_MODEL,
        fallback_to_oracle=False,
        gate=gate,
    )
    turn = run_orchestrator_turn(
        user_message="Why do I need to do this?",
        session=_tool_session(),
        llm=llm,
        correlation_id="corr-123",
    )

    disclosure = store.recent(limit=1)[0]
    assert disclosure.correlation_id == "corr-123"
    assert turn.llm_trace is not None
    assert turn.llm_trace.correlation_id == "corr-123"
    assert turn.llm_trace.disclosure_id == disclosure.id
    assert {item.get("correlation_id") for item in turn.turn_items} == {"corr-123"}
    assert turn.tool_calls
    assert turn.tool_calls[0].name == "world.explain"
    assert disclosure.tool_trace
    assert disclosure.tool_trace[0]["request"]["name"] == "world.explain"
    assert disclosure.enigma_actions
    assert disclosure.enigma_actions[0]["effect"] == "allowed"


def test_exact_outbound_payload_is_the_bytes_handed_to_fireworks() -> None:
    captured: list[bytes] = []

    def _urlopen(req: object, timeout: float = 0) -> _FakeResponse:
        captured.append(getattr(req, "data", b""))
        return _FakeResponse(_world_explain_payload())

    store = InMemoryDisclosureStore()
    gate = build_audited_egress_gate(
        remote_config=RemoteInferenceConfig(enabled=True),
        disclosure_store=store,
        fireworks_api_key="fw-test",
        fireworks_urlopen=_urlopen,
    )
    llm = EgressConversationLLM(
        provider="fireworks",
        api_key="fw-test",
        model=FIREWORKS_MODEL,
        fallback_to_oracle=False,
        gate=gate,
    )
    turn = run_orchestrator_turn(
        user_message="Why do I need to do this?",
        session=_tool_session(),
        llm=llm,
        correlation_id="corr-123",
    )

    wire = json.loads(captured[0].decode("utf-8"))
    disclosure = store.recent(limit=1)[0]
    outbound = disclosure.outbound_payload
    assert outbound["model"] == wire["model"]
    assert outbound["tools"] == wire["tools"]
    user_content = json.loads(outbound["messages"][1]["content"])
    wire_user = json.loads(wire["messages"][1]["content"])
    assert user_content == wire_user
    assert user_content["user_message"] == "Why do I need to do this?"
    assert user_content["conversation"]["current_subject_id"] == TOKEN_ID
    assert user_content["conversation"]["current_subject_kind"] == "next_action"
    assert "fw-test" not in json.dumps(outbound)
    assert "Authorization" not in json.dumps(outbound)

    sent = turn.llm_trace.remote_context_sent if turn.llm_trace else None
    assert sent is not None
    assert sent["user_message"] == "Why do I need to do this?"
    assert sent["conversation"]["current_subject_id"] == TOKEN_ID
    assert "message_word_count" not in sent
    dumped = json.dumps(disclosure.model_dump(mode="json"))
    assert "From:" not in dumped
    assert "@" not in dumped
