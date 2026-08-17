"""Structured LLM judge output — judge-v1 canonical contract (R-L02)."""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Literal

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


def parse_judge_v1_output(text: str) -> JudgeV1Output:
    stripped = text.strip()
    if not stripped:
        raise JudgeV1ParseError("empty LLM response")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise JudgeV1ParseError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise JudgeV1ParseError(f"expected JSON object, got {type(payload).__name__}")
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
    "JudgeV1Attention",
    "JudgeV1Output",
    "JudgeV1ParseError",
    "LlmJudgeParseError",
    "NextActionV1",
    "ReasonCode",
    "parse_judge_v1_output",
    "parse_llm_judge_output",
    "validate_evidence_ids",
]
