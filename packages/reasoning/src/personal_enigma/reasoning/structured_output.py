"""Structured LLM judge output — judge-v1 canonical contract (R-L02)."""

from __future__ import annotations

import json
import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from personal_enigma.domain.enums import ActionCategory


class ReasonCode(StrEnum):
    USER_COMMITMENT = "USER_COMMITMENT"
    DEADLINE_APPROACHING = "DEADLINE_APPROACHING"
    SOCIAL_COORDINATION = "SOCIAL_COORDINATION"
    ADMIN_FRICTION = "ADMIN_FRICTION"
    LOW_VALUE_NOISE = "LOW_VALUE_NOISE"
    LOW_URGENCY = "LOW_URGENCY"
    CONTEXT_ONLY = "CONTEXT_ONLY"
    CROSS_SOURCE_MATCH = "CROSS_SOURCE_MATCH"
    FOLLOW_UP_REQUIRED = "FOLLOW_UP_REQUIRED"
    UNRESOLVED_THREAD = "UNRESOLVED_THREAD"
    PENDING_REPLY = "PENDING_REPLY"
    OTHER = "OTHER"


class JudgeV1Attention(BaseModel):
    decision: Literal["surface", "suppress", "context"]
    priority: int = Field(ge=0, le=5)
    confidence: float = Field(ge=0.0, le=1.0)
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("reason_codes", mode="before")
    @classmethod
    def _coerce_reason_codes(cls, value: object) -> list[ReasonCode]:
        if not isinstance(value, list):
            return value  # type: ignore[return-value]
        allowed = {c.value for c in ReasonCode}
        return [
            ReasonCode(item) if str(item) in allowed else ReasonCode.OTHER
            for item in value
        ]


class NextActionV1(BaseModel):
    title: str
    action_type: ActionCategory = ActionCategory.ADMIN
    estimated_minutes: int | None = Field(default=None, ge=1)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)

    @field_validator("action_type", mode="before")
    @classmethod
    def _coerce_action_type(cls, value: object) -> ActionCategory:
        if isinstance(value, ActionCategory):
            return value
        try:
            return ActionCategory(str(value))
        except ValueError:
            return ActionCategory.ADMIN


class JudgeV1Output(BaseModel):
    schema_version: Literal["judge-v1"] = "judge-v1"
    attention: JudgeV1Attention
    next_action: NextActionV1 | None = None


JUDGE_V1_EXAMPLE: dict[str, Any] = {
    "schema_version": "judge-v1",
    "attention": {
        "decision": "surface",
        "priority": 4,
        "confidence": 0.85,
        "reason_codes": ["USER_COMMITMENT"],
        "evidence_ids": ["rem-example"],
    },
    "next_action": None,
}

JUDGE_V1_EXAMPLE_JSON = json.dumps(JUDGE_V1_EXAMPLE, indent=2)

JUDGE_V1_SYSTEM_PROMPT = (
    "You are Enigma's reasoning judge. Reason only over the sanitised context "
    "in the user message. Do not invent private identifiers.\n"
    "Attention semantics: surface = warrants the user's attention now; "
    "suppress = no useful intervention at this instant; context = genuine but "
    "non-urgent info when no current intervention is useful. "
    "Open obligation alone is not sufficient for surface. "
    "Important ≠ needs attention now; open ≠ urgent; candidate ≠ alert. "
    "Zero surfaced items across all candidates is valid.\n"
    "Return exactly one JSON object matching schema judge-v1 — no markdown "
    "fences, no chain-of-thought, no error placeholders.\n"
    f"Example shape:\n{JUDGE_V1_EXAMPLE_JSON}\n"
    "Required top-level keys: schema_version, attention (decision, priority, "
    "confidence, reason_codes, evidence_ids). next_action may be null.\n"
    'Never return {"name": "Invalid", ...} or other non-judge-v1 shapes.'
)


def judge_v1_response_format() -> dict[str, Any]:
    """Fireworks/OpenAI-compatible structured output for judge-v1."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "judge_v1_output",
            "schema": JudgeV1Output.model_json_schema(),
        },
    }


class JudgeV1ParseError(ValueError):
    """Structured judge-v1 output could not be parsed or validated."""


class InvalidEvidenceIdsError(ValueError):
    """Model cited evidence_ids absent from the allowed set."""


LlmJudgeParseError = JudgeV1ParseError


def validate_evidence_ids(output: JudgeV1Output, allowed: set[str]) -> None:
    unknown = set(output.attention.evidence_ids) - allowed
    if unknown:
        raise InvalidEvidenceIdsError(
            f"evidence_ids not in snapshot: {sorted(unknown)}"
        )


_TRANSPORT_ERROR_PREFIXES = ("[fireworks transport", "[openai transport")


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _strip_redacted_thinking(text: str) -> str:
    """Remove gpt-oss thinking wrappers; keep text after the closing tag."""
    return re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL,
    ).strip()


def describe_llm_text_shape(text: str) -> str:
    """Compact summary of model text for parse-failure debug (no secrets)."""
    stripped = text.strip()
    return (
        f"len={len(stripped)} has_brace={'{' in stripped} "
        f"has_harmony_final={'<|channel|>final<|message|>' in stripped} "
        f"has_redacted_thinking={'<think>' in stripped} "
        f"preview={stripped[:80]!r}"
    )


def _extract_harmony_final(text: str) -> str:
    marker = "<|channel|>final<|message|>"
    idx = text.rfind(marker)
    if idx >= 0:
        return text[idx + len(marker) :].strip()
    return text


def _is_rejection_payload(payload: dict[str, Any]) -> bool:
    """Fireworks / json-mode placeholder when the model cannot emit judge-v1."""
    if payload.get("name") == "Invalid":
        return True
    if "attention" not in payload and payload.get("schema_version") != "judge-v1":
        reason = payload.get("reason") or payload.get("message") or payload.get("error")
        if isinstance(reason, str) and reason.strip():
            return True
    return False


def _extract_first_json_object(text: str) -> str:
    """Return substring of the first parseable JSON object (ignore trailing blobs)."""
    decoder = json.JSONDecoder()
    start = 0
    while start < len(text):
        brace = text.find("{", start)
        if brace < 0:
            break
        try:
            _, end = decoder.raw_decode(text, brace)
            return text[brace:end]
        except json.JSONDecodeError:
            start = brace + 1
    raise JudgeV1ParseError(
        f"no JSON object found in LLM response ({describe_llm_text_shape(text)})"
    )


def extract_judge_v1_json_text(text: str) -> str:
    """Normalize model text to a JSON object string before ``json.loads``."""
    stripped = text.strip()
    if not stripped:
        raise JudgeV1ParseError(f"empty LLM response ({describe_llm_text_shape(text)})")
    lowered = stripped.lower()
    for prefix in _TRANSPORT_ERROR_PREFIXES:
        if lowered.startswith(prefix):
            raise JudgeV1ParseError(
                f"transport error (not model JSON): {stripped[:240]}"
            )
    candidate = _extract_harmony_final(
        _strip_redacted_thinking(_strip_markdown_fences(stripped))
    )
    return _extract_first_json_object(candidate)


def parse_judge_v1_output(text: str) -> JudgeV1Output:
    try:
        json_text = extract_judge_v1_json_text(text)
    except JudgeV1ParseError:
        raise
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise JudgeV1ParseError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise JudgeV1ParseError(f"expected JSON object, got {type(payload).__name__}")
    if _is_rejection_payload(payload):
        detail = payload.get("reason") or payload.get("message") or payload.get("name")
        raise JudgeV1ParseError(
            f"model rejection (not judge-v1): {detail!s}"[:240]
        )
    if payload.get("schema_version") not in (None, "judge-v1"):
        raise JudgeV1ParseError(
            f"unsupported schema_version: {payload.get('schema_version')!r}"
        )
    try:
        return JudgeV1Output.model_validate(payload)
    except ValidationError as exc:
        raise JudgeV1ParseError(f"schema validation failed: {exc}") from exc


def parse_llm_judge_output(text: str) -> JudgeV1Output:
    return parse_judge_v1_output(text)


__all__ = [
    "InvalidEvidenceIdsError",
    "JUDGE_V1_EXAMPLE",
    "JUDGE_V1_EXAMPLE_JSON",
    "JUDGE_V1_SYSTEM_PROMPT",
    "JudgeV1Attention",
    "JudgeV1Output",
    "JudgeV1ParseError",
    "LlmJudgeParseError",
    "NextActionV1",
    "ReasonCode",
    "describe_llm_text_shape",
    "extract_judge_v1_json_text",
    "judge_v1_response_format",
    "parse_judge_v1_output",
    "parse_llm_judge_output",
    "validate_evidence_ids",
]
