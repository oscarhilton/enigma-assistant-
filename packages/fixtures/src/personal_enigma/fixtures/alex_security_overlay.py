"""Alex v0.2.1 security overlay — opt-in only, never behavioural truth.

Structure enforced here::

    Alex v0.2.1
    ├─ authored behavioural timeline (``scenarios/alex-v1/``)
    ├─ background/noise corpus (``noise.yaml``, ``background.yaml``)
    └─ security overlay (OPT-IN ONLY)
       └─ ``alex_sensitive_canaries.py``

Normal attention/evaluation runs must **not** load canaries unless an explicit
security profile requests them (``ENIGMA_SECURITY_PROFILE=1`` or
``load_security_overlay=True``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from personal_enigma.fixtures.alex_sensitive_canaries import (
    ALEX_SENSITIVE_CANARIES,
    SensitiveCanary,
)

SECURITY_OVERLAY = "alex-security-overlay-v1"
ALEX_SCENARIO_ID = "alex-v1"
ALEX_SCENARIO_VERSION = "0.2.1"

_REPO_ROOT = Path(__file__).resolve().parents[5]
ALEX_SCENARIO_ROOT = _REPO_ROOT / "scenarios" / ALEX_SCENARIO_ID


def security_profile_enabled() -> bool:
    """True when ``ENIGMA_SECURITY_PROFILE`` is set to a truthy value."""
    return os.environ.get("ENIGMA_SECURITY_PROFILE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def resolve_load_security_overlay(*, load_security_overlay: bool | None = None) -> bool:
    """Resolve overlay flag: explicit arg beats environment."""
    if load_security_overlay is not None:
        return load_security_overlay
    return security_profile_enabled()


def load_security_overlay(
    *, load_security_overlay: bool | None = None,
) -> tuple[SensitiveCanary, ...]:
    """Return canaries only when security profile is explicitly enabled."""
    if not resolve_load_security_overlay(load_security_overlay=load_security_overlay):
        return ()
    return ALEX_SENSITIVE_CANARIES


@dataclass(frozen=True, slots=True)
class AlexFixtureContext:
    """Alex demo/evaluation fixture roots — behavioural truth vs overlay."""

    scenario_id: str
    scenario_version: str
    scenario_root: Path
    security_overlay: tuple[SensitiveCanary, ...]
    security_overlay_enabled: bool


def load_alex_fixture_context(*, load_security_overlay: bool | None = None) -> AlexFixtureContext:
    """Load Alex behavioural corpus paths; canaries only when opted in."""
    enabled = resolve_load_security_overlay(load_security_overlay=load_security_overlay)
    overlay = ALEX_SENSITIVE_CANARIES if enabled else ()
    return AlexFixtureContext(
        scenario_id=ALEX_SCENARIO_ID,
        scenario_version=ALEX_SCENARIO_VERSION,
        scenario_root=ALEX_SCENARIO_ROOT,
        security_overlay=overlay,
        security_overlay_enabled=enabled,
    )


__all__ = [
    "ALEX_SCENARIO_ID",
    "ALEX_SCENARIO_ROOT",
    "ALEX_SCENARIO_VERSION",
    "AlexFixtureContext",
    "SECURITY_OVERLAY",
    "load_alex_fixture_context",
    "load_security_overlay",
    "resolve_load_security_overlay",
    "security_profile_enabled",
]
