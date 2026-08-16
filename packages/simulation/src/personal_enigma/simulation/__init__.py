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
from personal_enigma.simulation.scenario import (
    ScenarioPackage,
    ScenarioValidationError,
    discover_scenarios,
    load_scenario,
    try_load_scenario,
)
from personal_enigma.simulation.scenario_rng import scenario_rng

__all__ = [
    "DEMO_BANNER_TEXT",
    "PRIVATE_CREDENTIAL_KEYS",
    "Clock",
    "DemoEnvironment",
    "EnvironmentMode",
    "PrivateEnvironment",
    "RealSourceAccessError",
    "ScenarioPackage",
    "ScenarioValidationError",
    "SecretNamespace",
    "SimulationClock",
    "SimulationEvent",
    "SystemClock",
    "assert_source_allowed_for_mode",
    "build_environment",
    "discover_scenarios",
    "environment_mode_from_env",
    "load_scenario",
    "scenario_rng",
    "storage_root_for",
    "try_load_scenario",
]
