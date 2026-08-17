"""Tests for judge-v1 structured output (R-L02)."""

from __future__ import annotations

import json

import pytest

from personal_enigma.domain.enums import ActionCategory
from personal_enigma.reasoning.structured_output import (
    JudgeV1ParseError,
    parse_judge_v1_output,
)


def test_judge_v1_next_action_action_type_enum() -> None:
    payload = {
        "schema_version": "judge-v1",
        "attention": {
            "decision": "surface",
            "priority": 3,
            "confidence": 0.8,
            "reason_codes": ["USER_COMMITMENT"],
            "evidence_ids": ["rem-expenses"],
        },
        "next_action": {
            "title": "Gather receipts",
            "action_type": "admin",
            "estimated_minutes": 5,
            "confidence": 0.7,
        },
    }
    out = parse_judge_v1_output(json.dumps(payload))
    assert out.next_action is not None
    assert out.next_action.action_type == ActionCategory.ADMIN


def test_judge_v1_rejects_bad_schema_version() -> None:
    payload = {
        "schema_version": "judge-v0",
        "attention": {
            "decision": "suppress",
            "priority": 0,
            "confidence": 0.5,
            "reason_codes": [],
            "evidence_ids": [],
        },
        "next_action": None,
    }
    with pytest.raises(JudgeV1ParseError, match="schema_version"):
        parse_judge_v1_output(json.dumps(payload))


def test_judge_v1_null_next_action() -> None:
    payload = {
        "schema_version": "judge-v1",
        "attention": {
            "decision": "suppress",
            "priority": 0,
            "confidence": 0.99,
            "reason_codes": ["LOW_URGENCY"],
            "evidence_ids": [],
        },
        "next_action": None,
    }
    out = parse_judge_v1_output(json.dumps(payload))
    assert out.next_action is None


def test_judge_v1_strips_markdown_fences() -> None:
    payload = {
        "schema_version": "judge-v1",
        "attention": {
            "decision": "suppress",
            "priority": 0,
            "confidence": 0.9,
            "reason_codes": ["LOW_VALUE_NOISE"],
            "evidence_ids": [],
        },
        "next_action": None,
    }
    fenced = f"```json\n{json.dumps(payload)}\n```"
    out = parse_judge_v1_output(fenced)
    assert out.attention.decision == "suppress"


def test_judge_v1_extracts_harmony_final_channel() -> None:
    payload = {
        "schema_version": "judge-v1",
        "attention": {
            "decision": "surface",
            "priority": 4,
            "confidence": 0.9,
            "reason_codes": ["USER_COMMITMENT"],
            "evidence_ids": ["rem-brunch-book"],
        },
        "next_action": None,
    }
    harmony = (
        "<|channel|>analysis<|message|>thinking..."
        f"<|channel|>final<|message|>{json.dumps(payload)}"
    )
    out = parse_judge_v1_output(harmony)
    assert out.attention.decision == "surface"


def test_judge_v1_transport_stub_is_clear_error() -> None:
    with pytest.raises(JudgeV1ParseError, match="transport error"):
        parse_judge_v1_output("[fireworks transport error: HTTP 400: seed unsupported]")


def test_judge_v1_rejects_invalid_placeholder() -> None:
    payload = {
        "name": "Invalid",
        "reason": "Missing these required fields.",
    }
    with pytest.raises(JudgeV1ParseError, match="model rejection"):
        parse_judge_v1_output(json.dumps(payload))


def test_judge_v1_ignores_trailing_extra_json() -> None:
    """Regression: Fireworks may append a second blob after judge-v1 (Extra data)."""
    payload = {
        "schema_version": "judge-v1",
        "attention": {
            "decision": "surface",
            "priority": 4,
            "confidence": 0.88,
            "reason_codes": ["USER_COMMITMENT"],
            "evidence_ids": ["rem-brunch-book"],
        },
        "next_action": None,
    }
    judge_json = json.dumps(payload, indent=2)
    trailing = json.dumps({"name": "Invalid", "reason": "placeholder"}, indent=2)
    combined = f"{judge_json}\n{trailing}"
    out = parse_judge_v1_output(combined)
    assert out.attention.decision == "surface"


def test_judge_v1_ignores_trailing_harmony_after_json() -> None:
    payload = {
        "schema_version": "judge-v1",
        "attention": {
            "decision": "suppress",
            "priority": 0,
            "confidence": 0.95,
            "reason_codes": ["LOW_URGENCY"],
            "evidence_ids": [],
        },
        "next_action": None,
    }
    combined = (
        f"{json.dumps(payload, indent=2)}\n"
        "<|channel|>analysis<|message|>post-hoc reasoning\n"
    )
    out = parse_judge_v1_output(combined)
    assert out.attention.decision == "suppress"


def test_judge_v1_no_json_includes_text_shape() -> None:
    reasoning_only = "<|channel|>analysis<|message|>pure chain-of-thought prose"
    with pytest.raises(JudgeV1ParseError, match="no JSON object found") as exc_info:
        parse_judge_v1_output(reasoning_only)
    assert "has_brace=False" in str(exc_info.value)
    assert "has_harmony_final=False" in str(exc_info.value)


def test_judge_v1_strips_redacted_thinking_before_json() -> None:
    payload = {
        "schema_version": "judge-v1",
        "attention": {
            "decision": "suppress",
            "priority": 0,
            "confidence": 0.9,
            "reason_codes": ["LOW_URGENCY"],
            "evidence_ids": [],
        },
        "next_action": None,
    }
    wrapped = (
        "<think>Internal reasoning without JSON braces here.</think>\n"
        f"{json.dumps(payload)}"
    )
    out = parse_judge_v1_output(wrapped)
    assert out.attention.decision == "suppress"
