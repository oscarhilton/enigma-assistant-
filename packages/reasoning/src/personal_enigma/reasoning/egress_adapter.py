"""Convert egress gate results to PAYG reasoning results."""

from __future__ import annotations

from personal_enigma.privacy.egress.gate import EgressResult
from personal_enigma.reasoning.logging import UsageRecord
from personal_enigma.reasoning.modes import ReasoningMode
from personal_enigma.reasoning.protocol import ReasoningResult


def egress_result_to_reasoning(
    result: EgressResult,
    *,
    model: str,
) -> ReasoningResult:
    """Map an ``EgressResult`` to ``ReasoningResult`` for PAYG clients."""
    disclosure = result.disclosure
    if result.response is None or result.response.blocked:
        block_reason = (
            (result.response.block_reason if result.response is not None else None)
            or disclosure.block_reason
            or ""
        )
        return ReasoningResult(
            text=block_reason,
            model=model,
            usage=None,
            dry_run=False,
            metadata={
                "status": "blocked",
                "left_machine": "false",
                "block_reason": disclosure.block_reason or "",
            },
        )
    response = result.response
    usage = UsageRecord(
        model=model,
        mode=ReasoningMode.ENABLED,
        prompt_tokens=disclosure.prompt_tokens,
        completion_tokens=disclosure.completion_tokens,
        estimated_cost_usd=0.0,
        dry_run=False,
        metadata={"status": "ok", "correlation_id": disclosure.correlation_id},
    )
    metadata = dict(response.metadata)
    metadata.setdefault("status", "ok")
    return ReasoningResult(
        text=response.text,
        model=model,
        usage=usage,
        dry_run=False,
        metadata=metadata,
    )
