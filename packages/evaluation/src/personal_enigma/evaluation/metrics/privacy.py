"""Privacy metrics — wired to packages/privacy invariants."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from personal_enigma.domain import PrivatePerson
from personal_enigma.evaluation.observations import PrivacyProbe
from personal_enigma.privacy.invariants import (
    PrivacyInvariantError,
    assert_remote_payload_safe,
)
from personal_enigma.privacy.levels import PrivacyLevel
from personal_enigma.privacy.remote import RemoteInferenceConfig


@dataclass(frozen=True, slots=True)
class PrivacyMetrics:
    direct_identifier_leaks: int
    secret_like_leaks: int
    high_risk_payloads: int
    medium_risk_payloads: int
    reidentification_flags: int
    blocked_requests: int
    probes_checked: int
    failures: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, int]:
        return {
            "direct_identifier_leaks": self.direct_identifier_leaks,
            "secret_like_leaks": self.secret_like_leaks,
            "high_risk_payloads": self.high_risk_payloads,
            "medium_risk_payloads": self.medium_risk_payloads,
            "reidentification_flags": self.reidentification_flags,
            "blocked_requests": self.blocked_requests,
            "probes_checked": self.probes_checked,
        }


def direct_identifier_leaks(*, count: int) -> int:
    """Known direct-identifier leaks (must stay 0)."""
    return count


def _person_from_dict(raw: dict[str, Any]) -> PrivatePerson:
    return PrivatePerson.model_validate(raw)


def _privacy_level(value: str | None) -> PrivacyLevel:
    if value is None:
        return PrivacyLevel.MEDIUM
    try:
        return PrivacyLevel(value)
    except ValueError:
        return PrivacyLevel.MEDIUM


def evaluate_privacy_probes(probes: list[PrivacyProbe]) -> PrivacyMetrics:
    """Run each probe through ``assert_remote_payload_safe``."""
    direct = 0
    secrets = 0
    high_risk = 0
    medium_risk = 0
    reident = 0
    blocked = 0
    failures: list[str] = []

    remote = RemoteInferenceConfig(enabled=True)

    for probe in probes:
        if probe.was_blocked:
            blocked += 1
            continue
        people = [_person_from_dict(p) for p in probe.people]
        level = _privacy_level(probe.privacy_level)
        payload = dict(probe.payload)
        metadata = dict(payload.get("metadata") or {})
        if probe.source_type and "source_type" not in metadata:
            metadata["source_type"] = probe.source_type
        payload["metadata"] = metadata
        try:
            assert_remote_payload_safe(
                payload,
                people=people,
                remote=remote,
            )
        except PrivacyInvariantError as exc:
            message = str(exc)
            failures.append(f"{probe.id}: {message}")
            lower = message.lower()
            if (
                "email" in lower
                or "phone" in lower
                or "privateperson" in lower
                or "leaked" in lower
            ):
                direct += 1
            elif "re-ident" in lower or "reident" in lower:
                reident += 1
            else:
                secrets += 1
            if level in {PrivacyLevel.HIGH, PrivacyLevel.VERY_HIGH}:
                high_risk += 1
            elif level == PrivacyLevel.MEDIUM:
                medium_risk += 1

    return PrivacyMetrics(
        direct_identifier_leaks=direct_identifier_leaks(count=direct),
        secret_like_leaks=secrets,
        high_risk_payloads=high_risk,
        medium_risk_payloads=medium_risk,
        reidentification_flags=reident,
        blocked_requests=blocked,
        probes_checked=len(probes),
        failures=failures,
    )


__all__ = [
    "PrivacyMetrics",
    "direct_identifier_leaks",
    "evaluate_privacy_probes",
]
