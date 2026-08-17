"""Disclosure record storage — in-memory for Demo; encrypted audit/ for Private."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from personal_enigma.privacy.egress.disclosure import EgressDisclosure


@runtime_checkable
class DisclosureStore(Protocol):
    """Append-only store for egress disclosure records."""

    def append(self, disclosure: EgressDisclosure) -> str: ...

    def recent(self, *, limit: int = 50) -> list[EgressDisclosure]: ...


class InMemoryDisclosureStore:
    """Thread-unsafe in-memory disclosure store for Demo / tests."""

    def __init__(self) -> None:
        self._records: list[EgressDisclosure] = []

    def append(self, disclosure: EgressDisclosure) -> str:
        self._records.append(disclosure)
        return disclosure.id

    def recent(self, *, limit: int = 50) -> list[EgressDisclosure]:
        return list(reversed(self._records[-limit:]))


class AuditBackedDisclosureStore:
    """Persist disclosure metadata to encrypted ``audit/`` (SEC-01)."""

    def __init__(self, audit_store: Any) -> None:
        self._audit = audit_store
        self._cache: list[EgressDisclosure] = []

    def append(self, disclosure: EgressDisclosure) -> str:
        self._audit.append_record(
            event_type="egress.disclosure",
            payload_hash=disclosure.payload_hash,
            field_summary={
                "correlation_id": disclosure.correlation_id,
                "purpose": disclosure.purpose,
                "provider": disclosure.provider,
                "model": disclosure.model,
                "transformation_profile": disclosure.transformation_profile,
                "payload_field_summary": disclosure.payload_field_summary,
                "outbound_payload": disclosure.outbound_payload,
                "transport_endpoint": disclosure.transport_endpoint,
                "included": disclosure.included,
                "excluded": disclosure.excluded,
                "denied_capabilities": disclosure.denied_capabilities,
                "tool_trace": disclosure.tool_trace,
                "enigma_actions": disclosure.enigma_actions,
                "byte_count": disclosure.byte_count,
                "blocked": disclosure.blocked,
                "block_reason": disclosure.block_reason,
                "classification": disclosure.classification,
                "prompt_tokens": disclosure.prompt_tokens,
                "completion_tokens": disclosure.completion_tokens,
                "timestamp": disclosure.timestamp,
            },
        )
        self._cache.append(disclosure)
        return disclosure.id

    def recent(self, *, limit: int = 50) -> list[EgressDisclosure]:
        return list(reversed(self._cache[-limit:]))
