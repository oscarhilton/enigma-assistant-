"""OpenAI Chat Completions provider — gate-internal only."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from personal_enigma.privacy.egress.classification import RemoteSafeContext
from personal_enigma.privacy.egress.providers.base import ProviderResponse


class OpenAIEgressProvider:
    """HTTP transport for OpenAI-compatible chat APIs."""

    provider_name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_s: float = 60.0,
        urlopen: Any | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._urlopen = urlopen or request.urlopen

    def send(
        self,
        context: RemoteSafeContext,
        *,
        transformed_context: Any | None = None,
        rep: int = 0,
        seed: int | None = None,
        max_output_tokens: int | None = None,
    ) -> ProviderResponse:
        del transformed_context, rep, seed, max_output_tokens
        model = context.model
        if not self._api_key:
            return ProviderResponse(
                text="[openai egress: no API key — local stub response]",
                model=model,
                metadata={"status": "no_api_key_stub", "left_machine": "false"},
            )

        endpoint = f"{self._base_url}/chat/completions"
        body = dict(context.wire_body)
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
                text=f"[openai egress error: {exc}]",
                model=model,
                metadata={"status": "error", "left_machine": "true", **transport_meta},
                request_body=body,
            )

        choices = payload.get("choices") or []
        if not choices:
            return ProviderResponse(
                text="[openai egress error: empty choices]",
                model=model,
                metadata={"status": "error", "left_machine": "true", **transport_meta},
                request_body=body,
            )

        message = choices[0].get("message") or {}
        text = str(message.get("content") or "")
        if context.transformation_profile == "conversation_orchestrator_v1":
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
