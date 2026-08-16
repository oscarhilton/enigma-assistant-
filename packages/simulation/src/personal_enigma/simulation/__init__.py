"""Demo Mode simulation package (Phase 2).

Environment separation and clock stubs live here. Synthetic adapters are
pinned under ``sources/`` for D4. See ``docs/architecture/demo-mode.md``.
"""

from personal_enigma.simulation.clock import Clock, SimulationClock, SystemClock
from personal_enigma.simulation.environment import (
    DEMO_BANNER_TEXT,
    DemoEnvironment,
    EnvironmentMode,
    RealSourceAccessError,
    assert_source_allowed_for_mode,
    environment_mode_from_env,
    storage_root_for,
)
from personal_enigma.simulation.events import SimulationEvent

__all__ = [
    "DEMO_BANNER_TEXT",
    "Clock",
    "DemoEnvironment",
    "EnvironmentMode",
    "RealSourceAccessError",
    "SimulationClock",
    "SimulationEvent",
    "SystemClock",
    "assert_source_allowed_for_mode",
    "environment_mode_from_env",
    "storage_root_for",
]
