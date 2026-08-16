"""Demo Mode simulation package (Phase 2).

Environment separation and clock live here. Synthetic adapters are pinned
under ``sources/`` for D4. See ``docs/architecture/demo-mode.md``.
"""

from personal_enigma.simulation.clock import Clock, SimulationClock, SystemClock
from personal_enigma.simulation.environment import (
    DEMO_BANNER_TEXT,
    PRIVATE_CREDENTIAL_KEYS,
    DemoEnvironment,
    EnvironmentMode,
    PrivateEnvironment,
    RealSourceAccessError,
    SecretNamespace,
    assert_source_allowed_for_mode,
    build_environment,
    environment_mode_from_env,
    storage_root_for,
)
from personal_enigma.simulation.events import SimulationEvent

__all__ = [
    "DEMO_BANNER_TEXT",
    "PRIVATE_CREDENTIAL_KEYS",
    "Clock",
    "DemoEnvironment",
    "EnvironmentMode",
    "PrivateEnvironment",
    "RealSourceAccessError",
    "SecretNamespace",
    "SimulationClock",
    "SimulationEvent",
    "SystemClock",
    "assert_source_allowed_for_mode",
    "build_environment",
    "environment_mode_from_env",
    "storage_root_for",
]
