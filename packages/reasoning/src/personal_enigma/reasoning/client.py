"""PAYG reasoning service with disabled / dry-run / enabled modes."""

from __future__ import annotations

from personal_enigma.privacy.egress import AuditedEgressGate, build_audited_egress_gate
from personal_enigma.privacy.remote import RemoteInferenceConfig
from personal_enigma.reasoning.egress_adapter import egress_result_to_reasoning
from personal_enigma.reasoning.errors import ReasoningDisabledError
from personal_enigma.reasoning.logging import (
    NullUsageLogger,
    UsageLogger,
    UsageRecord,
)
from personal_enigma.reasoning.modes import ReasoningMode
from personal_enigma.reasoning.privacy_gate import assert_remote_safe
from personal_enigma.reasoning.protocol import PaygTransport, ReasoningResult
from personal_enigma.reasoning.transport import NullPaygTransport
from personal_enigma.transformation import TransformedContext


class PaygReasoningService:
    """Pluggable PAYG client: privacy gate first, network last (or never)."""

    def __init__(
        self,
        *,
        mode: ReasoningMode = ReasoningMode.DISABLED,
        transport: PaygTransport | None = None,
        gate: AuditedEgressGate | None = None,
        usage_logger: UsageLogger | None = None,
        default_model: str = "payg-default",
        egress_purpose: str = "reasoning.payg",
    ) -> None:
        self._mode = mode
        self._default_model = default_model
        self._egress_purpose = egress_purpose
        self._usage_logger: UsageLogger = usage_logger or NullUsageLogger()
        self._legacy_transport: PaygTransport | None = None
        if mode in {ReasoningMode.DISABLED, ReasoningMode.DRY_RUN}:
            self._gate: AuditedEgressGate | None = None
            self._transport: PaygTransport = NullPaygTransport()
        elif gate is not None:
            self._gate = gate
            self._transport = NullPaygTransport()
        elif transport is None:
            raise ValueError(
                "ENABLED mode requires an explicit AuditedEgressGate or PaygTransport; "
                "refusing a silent MockPaygTransport default that would mask misconfiguration"
            )
        else:
            self._gate = None
            self._legacy_transport = transport
            self._transport = transport

    @property
    def mode(self) -> ReasoningMode:
        return self._mode

    @property
    def usage_logger(self) -> UsageLogger:
        return self._usage_logger

    def reason(
        self,
        context: TransformedContext,
        *,
        prompt: str = "",
        model: str | None = None,
    ) -> ReasoningResult:
        """Reason over sanitised context. Refuses unsanitised / gated payloads."""
        resolved_model = model or self._default_model

        if self._mode is ReasoningMode.DISABLED:
            raise ReasoningDisabledError(
                "remote reasoning is disabled; Apple / local ingestion must still work"
            )

        safe = assert_remote_safe(context)

        if self._mode is ReasoningMode.DRY_RUN:
            usage = UsageRecord(
                model=resolved_model,
                mode=ReasoningMode.DRY_RUN,
                prompt_tokens=_estimate_tokens(prompt, safe),
                completion_tokens=0,
                estimated_cost_usd=0.0,
                dry_run=True,
                metadata={"status": "dry_run_no_network"},
            )
            self._usage_logger.log_usage(usage)
            return ReasoningResult(
                text="",
                model=resolved_model,
                usage=usage,
                dry_run=True,
                metadata={"status": "dry_run_no_network"},
            )

        if self._gate is not None:
            egress = self._gate.submit(
                safe,
                purpose=self._egress_purpose,
                prompt=prompt,
                model=resolved_model,
                transformed_context=safe,
            )
            result = egress_result_to_reasoning(egress, model=resolved_model)
        else:
            assert self._legacy_transport is not None
            result = self._legacy_transport.complete(
                model=resolved_model, prompt=prompt, context=safe
            )

        if result.usage is not None:
            self._usage_logger.log_usage(result.usage)
        return result


def build_reasoning_client(
    *,
    mode: ReasoningMode | str = ReasoningMode.DISABLED,
    transport: PaygTransport | None = None,
    gate: AuditedEgressGate | None = None,
    usage_logger: UsageLogger | None = None,
    default_model: str = "payg-default",
    remote_config: RemoteInferenceConfig | None = None,
) -> PaygReasoningService:
    """Factory used by api/worker wiring. Defaults to disabled (no network)."""
    if isinstance(mode, ReasoningMode):
        resolved = mode
    else:
        try:
            resolved = ReasoningMode(mode)
        except ValueError as exc:
            allowed = ", ".join(repr(m.value) for m in ReasoningMode)
            raise ValueError(
                f"Invalid reasoning mode {mode!r}; allowed values: {allowed}"
            ) from exc
    resolved_gate = gate
    if resolved is ReasoningMode.ENABLED and resolved_gate is None and transport is not None:
        resolved_gate = build_audited_egress_gate(
            remote_config=remote_config or RemoteInferenceConfig(enabled=True),
        )
        transport = None
    return PaygReasoningService(
        mode=resolved,
        transport=transport,
        gate=resolved_gate,
        usage_logger=usage_logger,
        default_model=default_model,
    )


def _estimate_tokens(prompt: str, context: TransformedContext) -> int:
    words = len(prompt.split()) + len(context.summary.split()) + len(context.entities)
    return max(1, words)
