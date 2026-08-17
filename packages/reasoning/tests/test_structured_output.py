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
