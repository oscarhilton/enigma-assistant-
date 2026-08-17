"""OpenAI Chat Completions transport — sanitised TransformedContext only (M19)."""

from __future__ import annotations

import os
from typing import Any

from personal_enigma.privacy.egress import RemoteSafeContext, build_audited_egress_gate
from personal_enigma.privacy.remote import RemoteInferenceConfig
from personal_enigma.reasoning.egress_adapter import egress_result_to_reasoning
from personal_enigma.reasoning.logging import UsageRecord
from personal_enigma.reasoning.modes import ReasoningMode
from personal_enigma.reasoning.protocol import ReasoningResult
from personal_enigma.transformation import TransformedContext


class OpenAIChatTransport:
    """HTTP transport for OpenAI-compatible chat APIs.

    Never receives PrivatePerson / wholesale notes — only TransformedContext.
    All network I/O routes through ``AuditedEgressGate``.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_s: float = 30.0,
        urlopen: Any | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._urlopen = urlopen

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        context: TransformedContext,
    ) -> ReasoningResult:
        if not self._api_key:
            return ReasoningResult(
                text="[openai transport: no API key — local stub response]",
                model=model,
                usage=UsageRecord(
                    model=model,
                    mode=ReasoningMode.ENABLED,
                    prompt_tokens=0,
                    completion_tokens=0,
                    estimated_cost_usd=0.0,
                    dry_run=False,
                    metadata={"status": "no_api_key_stub"},
                ),
                dry_run=False,
                metadata={"status": "no_api_key_stub", "left_machine": "false"},
            )

        gate = build_audited_egress_gate(
            remote_config=RemoteInferenceConfig(enabled=True),
            openai_urlopen=self._urlopen,
        )
        remote_ctx = RemoteSafeContext.from_transformed(
            context,
            provider="openai",
            model=model,
            prompt=prompt,
        )
        result = gate.submit(
            remote_ctx,
            purpose="reasoning.openai_chat",
            transformed_context=context,
        )
        return egress_result_to_reasoning(result, model=model)
