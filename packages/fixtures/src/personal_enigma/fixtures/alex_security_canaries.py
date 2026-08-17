"""SEC manifest for Alex synthetic sensitive canary pack.

Wires ``alex_sensitive_canaries`` into SEC-02 egress assertions and SEC-07
shadow reconstruction benchmark specs. Complements ``adversarial_email_cases``
(injection corpus) with **sensitivity-tier** crash-test data.

All records are **FICTIONAL / SYNTHETIC** — never real personal data.
Load only via ``alex_security_overlay`` (opt-in); never part of behavioural truth.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from personal_enigma.fixtures.alex_sensitive_canaries import (
    ALEX_SENSITIVE_CANARIES,
    ALL_CANARY_SENTINELS,
    CANARY_BY_ID,
    SensitiveCanary,
    assert_canary_pack_complete,
)

PACK_ID = "alex-sensitive-canaries-v1"
PACK_DESCRIPTION = (
    "Synthetic HIGH-sensitivity canaries for Alex demo security regression. "
    "FICTIONAL only — used to assert sentinels never cross the egress wire and "
    "must not survive shadow strip (SEC-07)."
)


class GrepTargetId(StrEnum):
    """Four grep stages for canary regression (SEC-02 / SEC-07 / SEC-01)."""

    SOURCE = "source"
    REMOTE_EGRESS = "remote_egress"
    PERSISTENT_SHADOW = "persistent_shadow"
    STOLEN_DIRECTORY = "stolen_directory"


@dataclass(frozen=True, slots=True)
class GrepTarget:
    """One grep stage in the canary leakage pipeline."""

    target_id: GrepTargetId
    description: str
    must_contain_sentinels: bool


GREP_TARGETS: tuple[GrepTarget, ...] = (
    GrepTarget(
        target_id=GrepTargetId.SOURCE,
        description="Canary pack source bodies under fixtures/data/security_canaries/",
        must_contain_sentinels=True,
    ),
    GrepTarget(
        target_id=GrepTargetId.REMOTE_EGRESS,
        description="Remote egress payloads (SEC-02 wire assertions)",
        must_contain_sentinels=False,
    ),
    GrepTarget(
        target_id=GrepTargetId.PERSISTENT_SHADOW,
        description="Pseudonymous shadow layer export after strip (SEC-07)",
        must_contain_sentinels=False,
    ),
    GrepTarget(
        target_id=GrepTargetId.STOLEN_DIRECTORY,
        description="Copied private/ directory without Keychain (SEC-01)",
        must_contain_sentinels=False,
    ),
)


@dataclass(frozen=True, slots=True)
class SecurityCanaryManifestEntry:
    """One canary row in the SEC manifest."""

    canary_id: str
    category: str
    sensitivity_tier: str
    raw_marker: str
    sentinel_strings: tuple[str, ...]
    allowed_shadow_features: tuple[str, ...]
    forbidden_remote_semantics: tuple[str, ...]
    sec_ticket_refs: tuple[str, ...]


def security_canary_manifest() -> tuple[SecurityCanaryManifestEntry, ...]:
    return tuple(
        SecurityCanaryManifestEntry(
            canary_id=canary.id,
            category=canary.category,
            sensitivity_tier=canary.sensitivity,
            raw_marker=canary.raw_marker,
            sentinel_strings=canary.sentinel_strings,
            allowed_shadow_features=canary.allowed_shadow_features,
            forbidden_remote_semantics=canary.forbidden_remote_semantics,
            sec_ticket_refs=canary.sec_ticket_refs,
        )
        for canary in ALEX_SENSITIVE_CANARIES
    )


def forbidden_on_wire_sentinels() -> tuple[str, ...]:
    """Sentinel strings that must never appear in remote egress payloads."""
    return ALL_CANARY_SENTINELS


def reconstructability_probe_sentinels() -> tuple[str, ...]:
    """Sentinels SEC-07 reconstructability scorer must detect if shadow leaks."""
    return ALL_CANARY_SENTINELS


def grep_directory_for_sentinels(
    root: Path,
    sentinels: tuple[str, ...] | None = None,
) -> list[tuple[Path, str]]:
    """Return (path, sentinel) hits under *root* — empty list means PASS for shadow/egress."""
    needles = sentinels or ALL_CANARY_SENTINELS
    hits: list[tuple[Path, str]] = []
    for sentinel in needles:
        result = subprocess.run(
            ["rg", "-F", sentinel, str(root)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if ":" not in line:
                    continue
                file_part, _ = line.split(":", 1)
                hits.append((Path(file_part), sentinel))
    return hits


__all__ = [
    "GREP_TARGETS",
    "GrepTarget",
    "GrepTargetId",
    "PACK_DESCRIPTION",
    "PACK_ID",
    "SecurityCanaryManifestEntry",
    "assert_canary_pack_complete",
    "forbidden_on_wire_sentinels",
    "grep_directory_for_sentinels",
    "reconstructability_probe_sentinels",
    "security_canary_manifest",
    "ALEX_SENSITIVE_CANARIES",
    "CANARY_BY_ID",
    "SensitiveCanary",
]

# Re-export legacy alias at module level for importers expecting AlexSensitiveCanary.
AlexSensitiveCanary = SensitiveCanary
