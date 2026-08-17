"""Fireworks Chat Completions provider — gate-internal only (R-L03)."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from personal_enigma.privacy.egress.classification import RemoteSafeContext
from personal_enigma.privacy.egress.providers.base import ProviderResponse


class FireworksEgressProvider:
    """HTTP transport for Fireworks serverless Chat Completions."""

    provider_name = "fireworks"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.fireworks.ai/inference/v1",
        timeout_s: float = 60.0,
        max_output_tokens: int = 512,
        urlopen: Any | None = None,
        budget_hook: Any | None = None,
    ) -> None:
        self._api_key = (
            api_key if api_key is not None else os.environ.get("FIREWORKS_API_KEY", "")
        )
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._max_output_tokens = max_output_tokens
        self._urlopen = urlopen or request.urlopen
        self._budget_hook = budget_hook

    @property
    def budget_hook(self) -> Any | None:
        return self._budget_hook

    @budget_hook.setter
    def budget_hook(self, hook: Any | None) -> None:
        self._budget_hook = hook

    def send(
        self,
        context: RemoteSafeContext,
        *,
        transformed_context: Any | None = None,
        rep: int = 0,
        seed: int | None = None,
        max_output_tokens: int | None = None,
    ) -> ProviderResponse:
        from personal_enigma.reasoning.fireworks_transport import execute_fireworks_completion

        if context.transformation_profile in {
            "conversation_orchestrator_v1",
            "semantic_bootstrap_v1",
        }:
            return self._send_conversation(
                context, max_output_tokens=max_output_tokens
            )

        if transformed_context is None:
            return ProviderResponse(
                text="[fireworks egress error: missing TransformedContext]",
                model=context.model,
                blocked=True,
                block_reason="fireworks requires TransformedContext",
                metadata={"status": "error", "left_machine": "false"},
            )

        result = execute_fireworks_completion(
            prompt=context.prompt,
            context=transformed_context,
            model=context.model,
            api_key=self._api_key,
            base_url=self._base_url,
            timeout_s=self._timeout_s,
            max_output_tokens=max_output_tokens or self._max_output_tokens,
            urlopen=self._urlopen,
            budget_hook=self._budget_hook,
            rep=rep,
            seed=seed,
        )
        usage = result.usage
        return ProviderResponse(
            text=result.text,
            model=result.model,
            prompt_tokens=int(usage.prompt_tokens if usage else 0),
            completion_tokens=int(usage.completion_tokens if usage else 0),
            metadata=dict(result.metadata),
        )

    def _send_conversation(
        self,
        context: RemoteSafeContext,
        *,
        max_output_tokens: int | None = None,
    ) -> ProviderResponse:
        """OpenAI-compatible tool-calling path — same /chat/completions transport as reasoning."""
        model = context.model
        if not self._api_key:
            return ProviderResponse(
                text="[fireworks egress: no API key — local stub response]",
                model=model,
                metadata={"status": "no_api_key_stub", "left_machine": "false"},
            )

        endpoint = f"{self._base_url}/chat/completions"
        body = dict(context.wire_body)
        body.setdefault("max_tokens", max_output_tokens or self._max_output_tokens)
        req = request.Request(
            endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        transport_meta = {"transport_endpoint": endpoint}
        try:
            with self._urlopen(req, timeout=self._timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except error.URLError as exc:
            return ProviderResponse(
                text=f"[fireworks egress error: {exc}]",
                model=model,
                metadata={"status": "error", "left_machine": "true", **transport_meta},
                request_body=body,
            )

        choices = payload.get("choices") or []
        if not choices:
            return ProviderResponse(
                text="[fireworks egress error: empty choices]",
                model=model,
                metadata={"status": "error", "left_machine": "true", **transport_meta},
                request_body=body,
            )

        message = choices[0].get("message") or {}
        text = json.dumps(message)
        usage_raw = payload.get("usage") or {}
        return ProviderResponse(
            text=text,
            model=model,
            prompt_tokens=int(usage_raw.get("prompt_tokens", 0)),
            completion_tokens=int(usage_raw.get("completion_tokens", 0)),
            metadata={"status": "ok", "left_machine": "true", **transport_meta},
            request_body=body,
        )
