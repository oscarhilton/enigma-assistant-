"""Transports for PAYG reasoning (mock / null; real providers arrive later)."""

from __future__ import annotations

from personal_enigma.reasoning.errors import ReasoningDisabledError
from personal_enigma.reasoning.logging import UsageRecord
from personal_enigma.reasoning.modes import ReasoningMode
from personal_enigma.reasoning.protocol import ReasoningResult
from personal_enigma.transformation import TransformedContext


class NullPaygTransport:
    """Transport that must never be called (disabled / dry-run safety net)."""

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        context: TransformedContext,
    ) -> ReasoningResult:
        raise ReasoningDisabledError(
            "NullPaygTransport.complete was invoked — remote network must not open "
            "in disabled or dry-run mode"
        )


class MockPaygTransport:
    """In-process mock provider for tests — never opens a network connection."""

    def __init__(self, *, response_text: str = "mock-reasoning-ok") -> None:
        self.response_text = response_text
        self.calls: list[dict[str, object]] = []

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        context: TransformedContext,
    ) -> ReasoningResult:
        self.calls.append({"model": model, "prompt": prompt, "context": context})
        prompt_tokens = max(1, len(prompt.split()) + len(context.summary.split()))
        completion_tokens = max(1, len(self.response_text.split()))
        usage = UsageRecord(
            model=model,
            mode=ReasoningMode.ENABLED,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=round((prompt_tokens + completion_tokens) * 0.000002, 6),
            dry_run=False,
        )
        return ReasoningResult(
            text=self.response_text,
            model=model,
            usage=usage,
            dry_run=False,
            metadata={"provider": "mock"},
        )
