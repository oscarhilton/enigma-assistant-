"""PAYG reasoning service with disabled / dry-run / enabled modes."""

from __future__ import annotations

from personal_enigma.reasoning.errors import ReasoningDisabledError
from personal_enigma.reasoning.logging import InMemoryUsageLogger, UsageLogger, UsageRecord
from personal_enigma.reasoning.modes import ReasoningMode
from personal_enigma.reasoning.privacy_gate import assert_remote_safe
from personal_enigma.reasoning.protocol import PaygTransport, ReasoningResult
from personal_enigma.reasoning.transport import MockPaygTransport, NullPaygTransport
from personal_enigma.transformation import TransformedContext


class PaygReasoningService:
    """Pluggable PAYG client: privacy gate first, network last (or never)."""

    def __init__(
        self,
        *,
        mode: ReasoningMode = ReasoningMode.DISABLED,
        transport: PaygTransport | None = None,
        usage_logger: UsageLogger | None = None,
        default_model: str = "payg-default",
    ) -> None:
        self._mode = mode
        self._default_model = default_model
        self._usage_logger: UsageLogger = usage_logger or InMemoryUsageLogger()
        if mode in {ReasoningMode.DISABLED, ReasoningMode.DRY_RUN}:
            # Always install a null transport so accidental calls cannot hit the network.
            self._transport: PaygTransport = NullPaygTransport()
        else:
            self._transport = transport or MockPaygTransport()

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

        # ENABLED — transport may open a network connection.
        result = self._transport.complete(model=resolved_model, prompt=prompt, context=safe)
        if result.usage is not None:
            self._usage_logger.log_usage(result.usage)
        return result


def build_reasoning_client(
    *,
    mode: ReasoningMode | str = ReasoningMode.DISABLED,
    transport: PaygTransport | None = None,
    usage_logger: UsageLogger | None = None,
    default_model: str = "payg-default",
) -> PaygReasoningService:
    """Factory used by api/worker wiring. Defaults to disabled (no network)."""
    resolved = ReasoningMode(mode) if not isinstance(mode, ReasoningMode) else mode
    return PaygReasoningService(
        mode=resolved,
        transport=transport,
        usage_logger=usage_logger,
        default_model=default_model,
    )


def _estimate_tokens(prompt: str, context: TransformedContext) -> int:
    words = len(prompt.split()) + len(context.summary.split()) + len(context.entities)
    return max(1, words)
