"""Classify Arm B rep failures for live gate reporting (R-L09 / Phase 1)."""

from __future__ import annotations

from enum import StrEnum


class FailureClass(StrEnum):
    NONE = "none"
    PROVIDER_TRANSPORT_FAILURE = "provider_transport_failure"
    MODEL_TRUNCATION_FAILURE = "model_truncation_failure"
    MODEL_SCHEMA_FAILURE = "model_schema_failure"
    PRIVACY_GATE_FAILURE = "privacy_gate_failure"


def classify_parse_error(error: str | None) -> FailureClass:
    """Map a parse/transport error string to a failure class."""
    if not error:
        return FailureClass.NONE
    lower = error.lower()
    if "privacy" in lower or "remote_safe" in lower or "may_transmit" in lower:
        return FailureClass.PRIVACY_GATE_FAILURE
    if (
        "transport error" in lower
        or "fireworks transport" in lower
        or "http 403" in lower
        or "http 401" in lower
        or "http 429" in lower
        or "http 500" in lower
        or "http 502" in lower
        or "http 503" in lower
        or "error code: 1010" in lower
    ):
        return FailureClass.PROVIDER_TRANSPORT_FAILURE
    if (
        "truncat" in lower
        or "finish_reason=length" in lower
        or "no json object found" in lower
    ):
        return FailureClass.MODEL_TRUNCATION_FAILURE
    if (
        "schema validation" in lower
        or "unsupported schema_version" in lower
        or "invalid json" in lower
        or "model rejection" in lower
        or "evidence_ids" in lower
    ):
        return FailureClass.MODEL_SCHEMA_FAILURE
    return FailureClass.MODEL_SCHEMA_FAILURE


__all__ = ["FailureClass", "classify_parse_error"]
