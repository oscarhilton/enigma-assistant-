"""Fireworks Chat Completions transport — OpenAI-compatible, no Responses API (R-L03)."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any
from urllib import error, request

from personal_enigma.privacy import REMOTE_METADATA_KEYS
from personal_enigma.reasoning.logging import UsageRecord
from personal_enigma.reasoning.modes import ReasoningMode
from personal_enigma.reasoning.protocol import ReasoningResult
from personal_enigma.transformation import TransformedContext

DEFAULT_FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"
DEFAULT_FIREWORKS_MODEL = "accounts/fireworks/models/gpt-oss-120b"
DEFAULT_MAX_OUTPUT_TOKENS = 512


def default_fireworks_model() -> str:
    return os.environ.get("FIREWORKS_MODEL", DEFAULT_FIREWORKS_MODEL)


def fireworks_seed(*, checkpoint_id: str, rep: int) -> int:
    """Deterministic seed for a checkpoint repetition (stable across runs)."""
    digest = hashlib.sha256(f"{checkpoint_id}:{rep}".encode()).hexdigest()
    return int(digest[:8], 16) % (2**31 - 1)


class FireworksChatTransport:
    """HTTP transport for Fireworks serverless Chat Completions.

    Uses the OpenAI-compatible ``/chat/completions`` endpoint only — never the
    Responses API and never ``store=True``.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = DEFAULT_FIREWORKS_BASE_URL,
        timeout_s: float = 60.0,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        urlopen: Any | None = None,
    ) -> None:
        self._api_key = (
            api_key if api_key is not None else os.environ.get("FIREWORKS_API_KEY", "")
        )
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._max_output_tokens = max_output_tokens
        self._urlopen = urlopen or request.urlopen

    @property
    def max_output_tokens(self) -> int:
        return self._max_output_tokens

    def complete(
        self,
        *,
        model: str | None = None,
        prompt: str,
        context: TransformedContext,
        rep: int = 0,
        seed: int | None = None,
        max_output_tokens: int | None = None,
    ) -> ReasoningResult:
        resolved_model = model or default_fireworks_model()
        checkpoint_id = str(context.metadata.get("checkpoint_id", "unknown"))
        resolved_seed = seed if seed is not None else fireworks_seed(
            checkpoint_id=checkpoint_id, rep=rep
        )
        resolved_max_tokens = (
            max_output_tokens if max_output_tokens is not None else self._max_output_tokens
        )

        if not self._api_key:
            return ReasoningResult(
                text="[fireworks transport: no API key — local stub response]",
                model=resolved_model,
                usage=UsageRecord(
                    model=resolved_model,
                    mode=ReasoningMode.ENABLED,
                    prompt_tokens=0,
                    completion_tokens=0,
                    estimated_cost_usd=0.0,
                    dry_run=False,
                    metadata={"status": "no_api_key_stub"},
                ),
                dry_run=False,
                metadata={
                    "status": "no_api_key_stub",
                    "left_machine": "false",
                    "provider": "fireworks",
                },
            )

        body: dict[str, Any] = {
            "model": resolved_model,
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
                                "metadata": {
                                    key: value
                                    for key, value in context.metadata.items()
                                    if key in REMOTE_METADATA_KEYS
                                },
                            },
                        },
                        default=str,
                    ),
                },
            ],
            "max_tokens": resolved_max_tokens,
            "seed": resolved_seed,
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
            with self._urlopen(req, timeout=self._timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except error.URLError as exc:
            return ReasoningResult(
                text=f"[fireworks transport error: {exc}]",
                model=resolved_model,
                usage=None,
                dry_run=False,
                metadata={
                    "status": "error",
                    "left_machine": "true",
                    "provider": "fireworks",
                },
            )

        text = payload["choices"][0]["message"]["content"]
        usage_raw = payload.get("usage") or {}
        prompt_tokens = int(usage_raw.get("prompt_tokens", 0))
        completion_tokens = int(usage_raw.get("completion_tokens", 0))
        usage = UsageRecord(
            model=resolved_model,
            mode=ReasoningMode.ENABLED,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=0.0,
            dry_run=False,
            metadata={
                "status": "ok",
                "seed": str(resolved_seed),
                "checkpoint_id": checkpoint_id,
                "rep": str(rep),
            },
        )
        return ReasoningResult(
            text=text,
            model=resolved_model,
            usage=usage,
            dry_run=False,
            metadata={
                "status": "ok",
                "left_machine": "true",
                "provider": "fireworks",
                "seed": str(resolved_seed),
            },
        )
