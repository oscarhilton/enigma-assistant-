"""Fireworks Chat Completions transport — OpenAI-compatible, no Responses API (R-L03)."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any
from urllib import error, request

from personal_enigma.reasoning.logging import UsageRecord
from personal_enigma.reasoning.modes import ReasoningMode
from personal_enigma.reasoning.protocol import ReasoningResult
from personal_enigma.reasoning.structured_output import (
    JUDGE_V1_SYSTEM_PROMPT,
    SEMANTIC_JUDGE_V1_SYSTEM_PROMPT,
    SemanticJudgeV1ParseError,
    extract_judge_v1_json_text,
    judge_v1_response_format,
    parse_semantic_judge_v1_output,
    semantic_judge_v1_response_format,
)

JudgeArm = str  # "b1" | "b2" — evaluation benchmark arms only
from personal_enigma.transformation import TransformedContext

DEFAULT_FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"
DEFAULT_FIREWORKS_MODEL = "accounts/fireworks/models/gpt-oss-120b"
DEFAULT_MAX_OUTPUT_TOKENS = 512
# B2 semantic-judge-v1 emits more fields than judge-v1; 512 caused finish_reason=length.
DEFAULT_SEMANTIC_MAX_OUTPUT_TOKENS = 1024
SEMANTIC_LENGTH_RETRY_MAX_TOKENS = 1536
# gpt-oss defaults to medium CoT; judge-v1 needs completion budget for JSON in content.
DEFAULT_REASONING_EFFORT = "low"


def default_fireworks_model() -> str:
    return os.environ.get("FIREWORKS_MODEL", DEFAULT_FIREWORKS_MODEL)


def fireworks_seed(*, checkpoint_id: str, rep: int) -> int:
    """Deterministic seed for a checkpoint repetition (stable across runs)."""
    digest = hashlib.sha256(f"{checkpoint_id}:{rep}".encode()).hexdigest()
    return int(digest[:8], 16) % (2**31 - 1)


def _stringify_message_part(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for part in value:
            if isinstance(part, dict):
                text = (
                    part.get("text")
                    or part.get("content")
                    or part.get("output_text")
                )
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(part, str):
                parts.append(part)
        return "\n".join(parts)
    if isinstance(value, dict):
        return _stringify_message_part([value])
    if value is None:
        return ""
    return str(value)


def describe_message_shape(message: dict[str, Any]) -> str:
    """Compact, non-secret summary of an assistant message for parse-failure debug."""
    content = _stringify_message_part(message.get("content"))
    reasoning = _stringify_message_part(message.get("reasoning_content"))
    parsed = message.get("parsed")
    bits = [
        f"content_len={len(content)}",
        f"content_has_brace={'{' in content}",
        f"reasoning_len={len(reasoning)}",
        f"reasoning_has_final={'<|channel|>final<|message|>' in reasoning}",
        f"reasoning_has_brace={'{' in reasoning}",
        f"has_parsed={isinstance(parsed, dict)}",
    ]
    preview_source = content or reasoning
    if preview_source:
        preview = preview_source[:80].replace("\n", "\\n")
        bits.append(f"preview={preview!r}")
    return " ".join(bits)


def resolve_judge_arm(context: TransformedContext) -> JudgeArm:
    """Benchmark arm from context metadata; defaults to b1 (judge-v1)."""
    arm = str(context.metadata.get("judge_arm", "b1")).lower()
    return "b2" if arm == "b2" else "b1"


def _parsed_message_json(message: dict[str, Any]) -> str | None:
    """Fireworks json_schema may populate ``message.parsed`` with the object."""
    parsed = message.get("parsed")
    if isinstance(parsed, dict) and (
        parsed.get("schema_version") == "judge-v1"
        or parsed.get("schema_version") == "semantic-judge-v1"
        or "attention" in parsed
        or "obligation_strength" in parsed
    ):
        return json.dumps(parsed)
    return None


def _extract_message_content(message: dict[str, Any]) -> str:
    """Collect assistant text from structured / harmony / reasoning fields."""
    parsed_json = _parsed_message_json(message)
    if parsed_json is not None:
        return parsed_json

    content = _stringify_message_part(message.get("content"))
    reasoning = _stringify_message_part(message.get("reasoning_content"))
    if content and reasoning:
        return f"{content}\n{reasoning}"
    return content or reasoning


def _read_http_error_body(exc: error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", errors="replace").strip()
    except OSError:
        return str(exc.reason)


def _format_transport_error(exc: BaseException, *, detail: str = "") -> str:
    if isinstance(exc, error.HTTPError):
        resolved = detail or str(exc.reason)
        return f"[fireworks transport error: HTTP {exc.code}: {resolved}]"
    return f"[fireworks transport error: {exc}]"


def _should_retry_without_seed(*, status_code: int, detail: str) -> bool:
    if status_code != 400:
        return False
    lowered = detail.lower()
    return "seed" in lowered or "unsupported" in lowered


def _api_error_message(payload: dict[str, Any]) -> str | None:
    err = payload.get("error")
    if isinstance(err, dict):
        message = err.get("message") or err.get("type")
        if message:
            return str(message)
    if isinstance(err, str) and err:
        return err
    return None


def _valid_judge_payload(payload: dict[str, Any], *, judge_arm: JudgeArm) -> bool:
    if judge_arm == "b2":
        return payload.get("schema_version") == "semantic-judge-v1" or (
            "obligation_strength" in payload and "user_responsibility" in payload
        )
    return payload.get("schema_version") == "judge-v1" and "attention" in payload


def _model_rejection_detail(
    message: dict[str, Any], *, judge_arm: JudgeArm = "b1"
) -> str | None:
    """Detect Invalid placeholder in content when no valid judge JSON exists."""
    content = _stringify_message_part(message.get("content")).strip()
    if not content.startswith("{"):
        return None
    try:
        content_payload = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(content_payload, dict) or content_payload.get("name") != "Invalid":
        return None

    combined = _extract_message_content(message)
    try:
        json_text = extract_judge_v1_json_text(combined)
        payload = json.loads(json_text)
    except (json.JSONDecodeError, ValueError):
        payload = None
    if isinstance(payload, dict) and _valid_judge_payload(payload, judge_arm=judge_arm):
        return None

    detail = content_payload.get("reason") or content_payload.get("message") or "Invalid"
    return str(detail)


def _semantic_output_valid(text: str) -> bool:
    try:
        parse_semantic_judge_v1_output(text)
    except SemanticJudgeV1ParseError:
        return False
    return True


def _resolve_max_output_tokens(
    *,
    judge_arm: JudgeArm,
    max_output_tokens: int | None,
    transport_default: int,
) -> int:
    if max_output_tokens is not None:
        return max_output_tokens
    if judge_arm == "b2":
        return DEFAULT_SEMANTIC_MAX_OUTPUT_TOKENS
    return transport_default


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

    def _build_request_body(
        self,
        *,
        model: str,
        prompt: str,
        max_tokens: int,
        seed: int | None,
        judge_arm: JudgeArm = "b1",
    ) -> dict[str, Any]:
        if judge_arm == "b2":
            system_prompt = SEMANTIC_JUDGE_V1_SYSTEM_PROMPT
            response_format = semantic_judge_v1_response_format()
        else:
            system_prompt = JUDGE_V1_SYSTEM_PROMPT
            response_format = judge_v1_response_format()
        body: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "response_format": response_format,
            "reasoning_effort": DEFAULT_REASONING_EFFORT,
        }
        if seed is not None:
            body["seed"] = seed
        return body

    def _post_chat_completion(self, body: dict[str, Any]) -> dict[str, Any]:
        req = request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with self._urlopen(req, timeout=self._timeout_s) as resp:
            return json.loads(resp.read().decode("utf-8"))

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
        judge_arm = resolve_judge_arm(context)
        resolved_max_tokens = _resolve_max_output_tokens(
            judge_arm=judge_arm,
            max_output_tokens=max_output_tokens,
            transport_default=self._max_output_tokens,
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

        body = self._build_request_body(
            model=resolved_model,
            prompt=prompt,
            max_tokens=resolved_max_tokens,
            seed=resolved_seed,
            judge_arm=judge_arm,
        )
        seed_used = resolved_seed
        try:
            payload = self._post_chat_completion(body)
        except error.HTTPError as exc:
            detail = _read_http_error_body(exc)
            if resolved_seed is not None and _should_retry_without_seed(
                status_code=exc.code, detail=detail
            ):
                body = self._build_request_body(
                    model=resolved_model,
                    prompt=prompt,
                    max_tokens=resolved_max_tokens,
                    seed=None,
                    judge_arm=judge_arm,
                )
                seed_used = None
                try:
                    payload = self._post_chat_completion(body)
                except error.HTTPError as retry_exc:
                    retry_detail = _read_http_error_body(retry_exc)
                    return ReasoningResult(
                        text=_format_transport_error(retry_exc, detail=retry_detail),
                        model=resolved_model,
                        usage=None,
                        dry_run=False,
                        metadata={
                            "status": "error",
                            "left_machine": "true",
                            "provider": "fireworks",
                        },
                    )
            else:
                return ReasoningResult(
                    text=_format_transport_error(exc, detail=detail),
                    model=resolved_model,
                    usage=None,
                    dry_run=False,
                    metadata={
                        "status": "error",
                        "left_machine": "true",
                        "provider": "fireworks",
                    },
                )
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

        api_error = _api_error_message(payload)
        if api_error is not None:
            return ReasoningResult(
                text=f"[fireworks transport error: {api_error}]",
                model=resolved_model,
                usage=None,
                dry_run=False,
                metadata={
                    "status": "error",
                    "left_machine": "true",
                    "provider": "fireworks",
                },
            )

        choices = payload.get("choices") or []
        if not choices:
            return ReasoningResult(
                text="[fireworks transport error: empty choices in API response]",
                model=resolved_model,
                usage=None,
                dry_run=False,
                metadata={
                    "status": "error",
                    "left_machine": "true",
                    "provider": "fireworks",
                },
            )

        choice = choices[0]
        message = choice.get("message") or {}
        finish_reason = str(choice.get("finish_reason") or "")
        response_shape = describe_message_shape(message)
        rejection = _model_rejection_detail(message, judge_arm=judge_arm)
        if rejection is not None:
            return ReasoningResult(
                text=f"[fireworks transport error: model rejection: {rejection}]",
                model=resolved_model,
                usage=None,
                dry_run=False,
                metadata={
                    "status": "error",
                    "left_machine": "true",
                    "provider": "fireworks",
                    "finish_reason": finish_reason,
                    "response_shape": response_shape,
                },
            )
        text = _extract_message_content(message)
        retried_for_length = False
        if (
            judge_arm == "b2"
            and finish_reason == "length"
            and not _semantic_output_valid(text)
            and resolved_max_tokens < SEMANTIC_LENGTH_RETRY_MAX_TOKENS
        ):
            retry_body = self._build_request_body(
                model=resolved_model,
                prompt=prompt,
                max_tokens=SEMANTIC_LENGTH_RETRY_MAX_TOKENS,
                seed=seed_used,
                judge_arm=judge_arm,
            )
            try:
                retry_payload = self._post_chat_completion(retry_body)
            except (error.HTTPError, error.URLError):
                retry_payload = None
            if retry_payload is not None:
                retry_choices = retry_payload.get("choices") or []
                if retry_choices:
                    retry_choice = retry_choices[0]
                    retry_message = retry_choice.get("message") or {}
                    retry_text = _extract_message_content(retry_message)
                    if _semantic_output_valid(retry_text):
                        payload = retry_payload
                        choice = retry_choice
                        message = retry_message
                        finish_reason = str(retry_choice.get("finish_reason") or "")
                        response_shape = describe_message_shape(message)
                        text = retry_text
                        retried_for_length = True
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
                "seed": str(seed_used) if seed_used is not None else "",
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
                "seed": str(seed_used) if seed_used is not None else "",
                "finish_reason": finish_reason,
                "response_shape": response_shape,
                "retried_for_length": "true" if retried_for_length else "false",
            },
        )
