"""OpenAI Chat Completions transport — sanitised TransformedContext only (M19)."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from personal_enigma.reasoning.logging import UsageRecord
from personal_enigma.reasoning.modes import ReasoningMode
from personal_enigma.reasoning.protocol import ReasoningResult
from personal_enigma.transformation import TransformedContext


class OpenAIChatTransport:
    """HTTP transport for OpenAI-compatible chat APIs.

    Never receives PrivatePerson / wholesale notes — only TransformedContext.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_s: float = 30.0,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s

    def complete(
        self,
        *,
        model: str,
        prompt: str,
        context: TransformedContext,
    ) -> ReasoningResult:
        if not self._api_key:
            # Offline-safe fallback used in tests / disabled-key environments.
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

        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You reason only over the sanitised Enigma context. "
                        "Do not invent private identifiers."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "prompt": prompt,
                            "context": {
                                "summary": context.summary,
                                "entities": context.entities,
                                "metadata": context.metadata,
                            },
                        }
                    ),
                },
            ],
        }
        req = request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self._timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except error.URLError as exc:
            return ReasoningResult(
                text=f"[openai transport error: {exc}]",
                model=model,
                usage=None,
                dry_run=False,
                metadata={"status": "error", "left_machine": "true"},
            )

        text = payload["choices"][0]["message"]["content"]
        usage_raw = payload.get("usage") or {}
        usage = UsageRecord(
            model=model,
            mode=ReasoningMode.ENABLED,
            prompt_tokens=int(usage_raw.get("prompt_tokens", 0)),
            completion_tokens=int(usage_raw.get("completion_tokens", 0)),
            estimated_cost_usd=0.0,
            dry_run=False,
            metadata={"status": "ok"},
        )
        return ReasoningResult(
            text=text,
            model=model,
            usage=usage,
            dry_run=False,
            metadata={"status": "ok", "left_machine": "true"},
        )
