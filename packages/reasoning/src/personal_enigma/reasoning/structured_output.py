"""Structured LLM judge output schema (Reasoning Value Gate / R03)."""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class LlmJudgeAttention(BaseModel):
    item_id: str
    behaviour: Literal["surface", "suppress"]
    priority: int = Field(ge=1, le=5)


class LlmJudgeNextAction(BaseModel):
    title: str
    estimated_minutes: int | None = Field(default=None, ge=1)
    effort: Literal["trivial", "light", "moderate", "heavy"] | None = None
    why_this_now: str | None = None


class LlmJudgeOutput(BaseModel):
    attention: LlmJudgeAttention
    next_action: LlmJudgeNextAction


class LlmJudgeParseError(ValueError):
    """Structured output could not be parsed or validated."""


def parse_llm_judge_output(text: str) -> LlmJudgeOutput:
    stripped = text.strip()
    if not stripped:
        raise LlmJudgeParseError("empty LLM response")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LlmJudgeParseError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise LlmJudgeParseError(f"expected JSON object, got {type(payload).__name__}")
    try:
        return LlmJudgeOutput.model_validate(payload)
    except ValidationError as exc:
        raise LlmJudgeParseError(f"schema validation failed: {exc}") from exc


__all__ = [
    "LlmJudgeAttention",
    "LlmJudgeNextAction",
    "LlmJudgeOutput",
    "LlmJudgeParseError",
    "parse_llm_judge_output",
]
