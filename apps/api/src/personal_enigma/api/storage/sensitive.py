"""Sensitive inference write-path guardrails (SEC-06 pilot invariant)."""

from __future__ import annotations

from personal_enigma.domain.retention import (
    RetentionClass,
    SensitiveInferenceClass,
)

_SENSITIVE_KEYWORDS: dict[SensitiveInferenceClass, tuple[str, ...]] = {
    SensitiveInferenceClass.MEDICAL: (
        "diagnosis",
        "medication",
        "therapy",
        "hospital",
        "depression",
        "anxiety disorder",
    ),
    SensitiveInferenceClass.SEXUALITY: (
        "sexual orientation",
        "lgbtq",
        "coming out",
    ),
    SensitiveInferenceClass.POLITICAL: (
        "political affiliation",
        "voted for",
        "party member",
    ),
    SensitiveInferenceClass.SUBSTANCE: (
        "substance abuse",
        "addiction",
        "rehab",
        "alcoholism",
    ),
    SensitiveInferenceClass.INTIMATE_RELATIONSHIP: (
        "affair",
        "divorce proceedings",
        "intimate partner",
    ),
    SensitiveInferenceClass.FINANCIAL_DISTRESS: (
        "bankruptcy",
        "debt collector",
        "foreclosure",
        "payday loan",
    ),
    SensitiveInferenceClass.BEHAVIOURAL_ROUTINE: (
        "sleep pattern",
        "commute routine",
        "daily location pattern",
    ),
}


class SensitiveInferenceError(Exception):
    """Raised when a durable write would persist a pilot-forbidden inference class."""


def classify_sensitive_inference(text: str) -> SensitiveInferenceClass | None:
    """Return the first matching sensitive class for ``text``, or None."""
    lowered = text.lower()
    for cls, keywords in _SENSITIVE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return cls
    return None


def assert_durable_write_allowed(
    *,
    payload: dict[str, object],
    retention_class: RetentionClass,
) -> None:
    """Reject permanent storage of sensitive inference classes at write time."""
    if retention_class == RetentionClass.EPHEMERAL_ANSWER_ONLY:
        return
    haystack = " ".join(str(v) for v in payload.values()).lower()
    match = classify_sensitive_inference(haystack)
    if match is not None:
        raise SensitiveInferenceError(
            f"Durable storage rejected for sensitive inference class: {match.value}"
        )
