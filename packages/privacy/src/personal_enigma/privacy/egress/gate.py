"""Single audited remote egress gateway (SEC-02 / ADR-021)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4

from personal_enigma.privacy.egress.assert_remote_safe import assert_remote_safe
from personal_enigma.privacy.egress.classification import (
    PrivateDerived,
    PrivateRaw,
    RemoteSafeContext,
)
from personal_enigma.privacy.egress.disclosure import (
    CompiledTurnManifest,
    EgressDisclosure,
    redact_transport_secrets,
)
from personal_enigma.privacy.egress.errors import EgressBlockedError
from personal_enigma.privacy.egress.providers.base import EgressProvider, ProviderResponse
from personal_enigma.privacy.egress.providers.fireworks import FireworksEgressProvider
from personal_enigma.privacy.egress.providers.openai import OpenAIEgressProvider
from personal_enigma.privacy.egress.store import DisclosureStore, InMemoryDisclosureStore
from personal_enigma.privacy.remote import RemoteInferenceConfig, may_send_remotely
from personal_enigma.privacy.safe_logging import content_hash, format_safe_log_event
from personal_enigma.transformation import TransformedContext

_DEFAULT_GATE: AuditedEgressGate | None = None


class _Clock(Protocol):
    def now(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class EgressResult:
    """Outcome of an egress gate submission."""

    disclosure: EgressDisclosure
    response: ProviderResponse | None = None
    sent: bool = False


class AuditedEgressGate:
    """Sole production entry for remote-model HTTP in Private / live paths."""

    def __init__(
        self,
        *,
        remote_config: RemoteInferenceConfig | None = None,
        disclosure_store: DisclosureStore | None = None,
        providers: dict[str, EgressProvider] | None = None,
        clock: _Clock | None = None,
    ) -> None:
        self._remote_config = remote_config or RemoteInferenceConfig(enabled=False)
        self._store = disclosure_store or InMemoryDisclosureStore()
        self._providers: dict[str, EgressProvider] = providers or {
            "openai": OpenAIEgressProvider(),
            "fireworks": FireworksEgressProvider(),
        }
        self._clock = clock

    def _timestamp(self) -> str:
        if self._clock is None:
            return ""
        return self._clock.now().isoformat()

    @property
    def disclosure_store(self) -> DisclosureStore:
        return self._store

    @property
    def remote_config(self) -> RemoteInferenceConfig:
        return self._remote_config

    def send(
        self,
        context: Any,
        *,
        purpose: str,
        correlation_id: str | None = None,
        prompt: str = "",
        model: str = "",
        transformed_context: TransformedContext | None = None,
        rep: int = 0,
        seed: int | None = None,
        max_output_tokens: int | None = None,
    ) -> EgressResult:
        """Alias for ``submit`` — used in regression tests."""
        return self.submit(
            context,
            purpose=purpose,
            correlation_id=correlation_id,
            prompt=prompt,
            model=model,
            transformed_context=transformed_context,
            rep=rep,
            seed=seed,
            max_output_tokens=max_output_tokens,
        )

    def submit(
        self,
        context: Any,
        *,
        purpose: str,
        correlation_id: str | None = None,
        prompt: str = "",
        model: str = "",
        transformed_context: TransformedContext | None = None,
        rep: int = 0,
        seed: int | None = None,
        max_output_tokens: int | None = None,
    ) -> EgressResult:
        """Validate, audit, and optionally transmit a REMOTE_SAFE payload."""
        corr = correlation_id or uuid4().hex

        if isinstance(context, (PrivateRaw, PrivateDerived)):
            label = type(context).__name__
            return self._block(
                context=RemoteSafeContext(
                    transformation_profile="blocked",
                    provider="none",
                    model="none",
                    field_summary={"rejected_type": label},
                    may_transmit_remotely=False,
                ),
                purpose=purpose,
                correlation_id=corr,
                reason=f"{label} cannot cross egress gate",
                classification="private_raw"
                if isinstance(context, PrivateRaw)
                else "private_derived",
            )

        if isinstance(context, str):
            return self._block_unclassified(
                purpose=purpose,
                correlation_id=corr,
                payload_type="str",
                reason="raw string payloads cannot cross egress gate",
            )

        remote_ctx: RemoteSafeContext
        safe_transformed: TransformedContext | None = transformed_context

        if isinstance(context, RemoteSafeContext):
            remote_ctx = context
            if prompt:
                remote_ctx = context.model_copy(update={"prompt": prompt})
            if model:
                remote_ctx = remote_ctx.model_copy(update={"model": model})
        elif isinstance(context, TransformedContext):
            try:
                safe_transformed = assert_remote_safe(context)
            except EgressBlockedError as exc:
                return self._block_unclassified(
                    purpose=purpose,
                    correlation_id=corr,
                    payload_type=type(context).__name__,
                    reason=str(exc),
                )
            provider = "fireworks" if purpose.startswith("reasoning.") else "openai"
            resolved_model = model or str(context.metadata.get("model") or "payg-default")
            resolved_prompt = prompt or str(context.metadata.get("prompt") or "")
            remote_ctx = RemoteSafeContext.from_transformed(
                safe_transformed,
                provider=provider,
                model=resolved_model,
                prompt=resolved_prompt,
            )
        else:
            return self._block_unclassified(
                purpose=purpose,
                correlation_id=corr,
                payload_type=type(context).__name__,
                reason=f"unclassified payload type {type(context).__name__}",
            )

        wire_bytes = json.dumps(remote_ctx.wire_body, sort_keys=True, default=str).encode(
            "utf-8"
        )
        payload_hash = content_hash(wire_bytes)
        byte_count = len(wire_bytes)

        if not remote_ctx.may_transmit_remotely:
            return self._block(
                context=remote_ctx,
                purpose=purpose,
                correlation_id=corr,
                reason="payload may_transmit_remotely is False",
                payload_hash=payload_hash,
                byte_count=byte_count,
            )

        if not may_send_remotely(
            self._remote_config,
            payload_allows_remote=remote_ctx.may_transmit_remotely,
        ):
            return self._block(
                context=remote_ctx,
                purpose=purpose,
                correlation_id=corr,
                reason="RemoteInferenceConfig(enabled=False) — no HTTP",
                payload_hash=payload_hash,
                byte_count=byte_count,
            )

        provider = self._providers.get(remote_ctx.provider)
        if provider is None:
            return self._block(
                context=remote_ctx,
                purpose=purpose,
                correlation_id=corr,
                reason=f"unknown provider {remote_ctx.provider!r}",
                payload_hash=payload_hash,
                byte_count=byte_count,
            )

        if (
            remote_ctx.provider == "fireworks"
            and safe_transformed is None
            and remote_ctx.transformation_profile
            not in {"conversation_orchestrator_v1", "semantic_bootstrap_v1"}
        ):
            return self._block(
                context=remote_ctx,
                purpose=purpose,
                correlation_id=corr,
                reason="fireworks egress requires TransformedContext",
                payload_hash=payload_hash,
                byte_count=byte_count,
            )

        print(
            format_safe_log_event(
                "egress.transmit",
                correlation_id=corr,
                purpose=purpose,
                provider=remote_ctx.provider,
                model=remote_ctx.model,
                payload_hash=payload_hash,
                byte_count=byte_count,
            )
        )

        response = provider.send(
            remote_ctx,
            transformed_context=safe_transformed,
            rep=rep,
            seed=seed,
            max_output_tokens=max_output_tokens,
        )

        outbound = redact_transport_secrets(response.request_body or remote_ctx.wire_body)
        disclosure = EgressDisclosure(
            correlation_id=corr,
            timestamp=self._timestamp(),
            purpose=purpose,
            provider=remote_ctx.provider,
            model=remote_ctx.model,
            transformation_profile=remote_ctx.transformation_profile,
            payload_field_summary=dict(remote_ctx.field_summary),
            payload_hash=payload_hash,
            byte_count=byte_count,
            blocked=False,
            classification="remote_safe",
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            outbound_payload=outbound if isinstance(outbound, dict) else {},
            provider_response={
                "text": response.text,
                "model": response.model,
                "blocked": response.blocked,
                "block_reason": response.block_reason,
            },
            transport_endpoint=response.metadata.get("transport_endpoint") or None,
            included=list(remote_ctx.included),
            excluded=list(remote_ctx.excluded),
            denied_capabilities=list(remote_ctx.denied_capabilities),
            context_manifest=(
                CompiledTurnManifest.model_validate(remote_ctx.context_manifest)
                if remote_ctx.context_manifest
                else None
            ),
        )
        self._store.append(disclosure)
        return EgressResult(disclosure=disclosure, response=response, sent=True)

    def recent_disclosures(self, *, limit: int = 50) -> list[EgressDisclosure]:
        return self._store.recent(limit=limit)

    def attach_turn_outcome(
        self,
        disclosure_id: str,
        *,
        tool_trace: list[dict[str, Any]],
        enigma_actions: list[dict[str, Any]],
    ) -> None:
        """Stamp tool execution onto the same disclosure the gate already recorded."""
        for row in self._store.recent(limit=200):
            if row.id == disclosure_id:
                row.tool_trace = list(tool_trace)
                row.enigma_actions = list(enigma_actions)
                return

    def _block_unclassified(
        self,
        *,
        purpose: str,
        correlation_id: str,
        payload_type: str,
        reason: str,
    ) -> EgressResult:
        placeholder = RemoteSafeContext(
            transformation_profile="blocked",
            provider="none",
            model="none",
            field_summary={"rejected_type": payload_type},
            may_transmit_remotely=False,
        )
        return self._block(
            context=placeholder,
            purpose=purpose,
            correlation_id=correlation_id,
            reason=reason,
            classification="unclassified",
        )

    def _block(
        self,
        *,
        context: RemoteSafeContext,
        purpose: str,
        correlation_id: str,
        reason: str,
        payload_hash: str = "",
        byte_count: int = 0,
        classification: str = "remote_safe",
    ) -> EgressResult:
        print(
            format_safe_log_event(
                "egress.blocked",
                correlation_id=correlation_id,
                purpose=purpose,
                reason=reason,
            )
        )
        outbound = redact_transport_secrets(context.wire_body)
        disclosure = EgressDisclosure(
            correlation_id=correlation_id,
            timestamp=self._timestamp(),
            purpose=purpose,
            provider=context.provider,
            model=context.model,
            transformation_profile=context.transformation_profile,
            payload_field_summary=dict(context.field_summary),
            payload_hash=payload_hash or content_hash(reason.encode("utf-8")),
            byte_count=byte_count,
            blocked=True,
            block_reason=reason,
            classification=classification,
            outbound_payload=outbound if isinstance(outbound, dict) else {},
            included=list(context.included),
            excluded=list(context.excluded),
            denied_capabilities=list(context.denied_capabilities),
            context_manifest=(
                CompiledTurnManifest.model_validate(context.context_manifest)
                if context.context_manifest
                else None
            ),
        )
        self._store.append(disclosure)
        return EgressResult(
            disclosure=disclosure,
            response=ProviderResponse(
                text="",
                model=context.model,
                blocked=True,
                block_reason=reason,
                metadata={"status": "blocked", "left_machine": "false"},
            ),
            sent=False,
        )


def build_audited_egress_gate(
    *,
    remote_config: RemoteInferenceConfig | None = None,
    disclosure_store: DisclosureStore | None = None,
    openai_api_key: str | None = None,
    openai_urlopen: Any | None = None,
    fireworks_api_key: str | None = None,
    fireworks_urlopen: Any | None = None,
    fireworks_budget_hook: Any | None = None,
    clock: _Clock | None = None,
) -> AuditedEgressGate:
    """Factory for a gate with injectable provider backends (tests / evaluation)."""
    fireworks = FireworksEgressProvider(
        api_key=fireworks_api_key,
        urlopen=fireworks_urlopen,
    )
    if fireworks_budget_hook is not None:
        fireworks.budget_hook = fireworks_budget_hook
    return AuditedEgressGate(
        remote_config=remote_config,
        disclosure_store=disclosure_store,
        clock=clock,
        providers={
            "openai": OpenAIEgressProvider(api_key=openai_api_key, urlopen=openai_urlopen),
            "fireworks": fireworks,
        },
    )


def get_audited_egress_gate() -> AuditedEgressGate:
    """Process-wide default gate — lazy singleton."""
    global _DEFAULT_GATE
    if _DEFAULT_GATE is None:
        import os

        enabled = os.environ.get("ENIGMA_REASONING_MODE", "").lower() == "enabled"
        demo_llm = os.environ.get("ENIGMA_DEMO_LLM_CONVERSATION", "").lower() in (
            "1",
            "true",
            "yes",
        )
        remote_enabled = (
            enabled
            or demo_llm
            or bool(os.environ.get("OPENAI_API_KEY"))
            or bool(os.environ.get("FIREWORKS_API_KEY"))
        )
        _DEFAULT_GATE = build_audited_egress_gate(
            remote_config=RemoteInferenceConfig(enabled=remote_enabled),
        )
    return _DEFAULT_GATE


def set_audited_egress_gate(gate: AuditedEgressGate | None) -> None:
    """Replace the process-wide gate (tests)."""
    global _DEFAULT_GATE
    _DEFAULT_GATE = gate
