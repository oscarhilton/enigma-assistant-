"""Tests for live gate failure taxonomy (Phase 1)."""

from __future__ import annotations

from personal_enigma.evaluation.failure_class import FailureClass, classify_parse_error


def test_classify_transport_403() -> None:
    assert (
        classify_parse_error("Fireworks transport error: HTTP 403 error code: 1010")
        == FailureClass.PROVIDER_TRANSPORT_FAILURE
    )


def test_classify_truncation() -> None:
    assert (
        classify_parse_error("finish_reason=length: no json object found")
        == FailureClass.MODEL_TRUNCATION_FAILURE
    )


def test_classify_schema() -> None:
    assert (
        classify_parse_error("schema validation failed for evidence_ids")
        == FailureClass.MODEL_SCHEMA_FAILURE
    )


def test_classify_privacy() -> None:
    assert (
        classify_parse_error("privacy gate: may_transmit_remotely is false")
        == FailureClass.PRIVACY_GATE_FAILURE
    )


def test_classify_none() -> None:
    assert classify_parse_error(None) == FailureClass.NONE
