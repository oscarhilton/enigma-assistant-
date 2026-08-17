"""Tests for semantic-judge-v1 structured output parsing."""

from __future__ import annotations

import json

import pytest

from personal_enigma.reasoning.structured_output import (
    SemanticJudgeV1ParseError,
    parse_semantic_judge_v1_output,
)


def test_parse_semantic_judge_rejects_next_action_only_payload() -> None:
    payload = {"title": "Open expense spreadsheet", "estimated_minutes": 5}
    with pytest.raises(SemanticJudgeV1ParseError, match="truncated semantic output"):
        parse_semantic_judge_v1_output(json.dumps(payload))


def test_parse_semantic_judge_rejects_next_action_only_with_finish_reason_hint() -> None:
    """Regression: live B2 hit finish_reason=length leaving only next_action keys."""
    payload = {"title": "Open expense s", "estimated_minutes": 5}
    with pytest.raises(SemanticJudgeV1ParseError, match="next_action fields"):
        parse_semantic_judge_v1_output(json.dumps(payload))
