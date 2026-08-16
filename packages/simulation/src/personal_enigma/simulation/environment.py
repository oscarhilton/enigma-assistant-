"""Environment mode and Demo/Private/Shadow storage separation (D1 + S01)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, NoReturn

from personal_enigma.simulation.clock import Clock, SimulationClock, SystemClock

ENV_MODE = "ENIGMA_ENVIRONMENT_MODE"
ENV_ENIGMA_HOME = "ENIGMA_HOME"
ENV_PRIVATE_ROOT = "ENIGMA_PRIVATE_STORAGE_ROOT"
ENV_DEMO_ROOT = "ENIGMA_DEMO_STORAGE_ROOT"
ENV_SHADOW_ROOT = "ENIGMA_SHADOW_STORAGE_ROOT"

DEMO_BANNER_TEXT = "DEMO MODE — FICTIONAL DATA ONLY"
SHADOW_BANNER_TEXT = "SHADOW MODE — OBSERVATION ONLY · NOTIFICATIONS OFF"

# Credential keys that must never appear in a Demo secret namespace.
PRIVATE_CREDENTIAL_KEYS = frozenset(
    {
        "GOOGLE_CLIENT_SECRET",
        "GMAIL_TOKEN",
        "APPLE_BRIDGE_TOKEN",
        "PRIVATE_HMAC_KEY",
    }
)

# Real connectors live under ingestion; synthetic adapters will live under
# ``personal_enigma.simulation.sources`` (D4).
_REAL_SOURCE_MODULE_PREFIXES = (
    "personal_enigma.ingestion.sources.",
    "personal_enigma.ingestion.bridge_client",
)


class EnvironmentMode(StrEnum):
    """Runtime data environment — Demo, Private, or Shadow (Phase 3)."""

    DEMO = "demo"
    PRIVATE = "private"
    SHADOW = "shadow"


class RealSourceAccessError(RuntimeError):
    """Raised when Demo Mode attempts real connector access."""


class DemoDataMigrationError(RuntimeError):
    """Raised when Demo storage/secrets are migrated into Shadow or Private."""


def parse_environment_mode(value: str | None) -> EnvironmentMode:
    """Parse mode from config/env; default PRIVATE for safety."""
    if value is None or value.strip() == "":
        return EnvironmentMode.PRIVATE
    normalised = value.strip().lower()
    try:
        return EnvironmentMode(normalised)
    except ValueError as exc:
        raise ValueError(
            f"Unknown environment mode {value!r}; expected demo|private|shadow"
        ) from exc


def environment_mode_from_env() -> EnvironmentMode:
    """Read ``ENIGMA_ENVIRONMENT_MODE`` (default private)."""
    return parse_environment_mode(os.environ.get(ENV_MODE))


def default_enigma_home(*, home: Path | None = None) -> Path:
    """Return ``$ENIGMA_HOME`` or ``~/.enigma``."""
    override = os.environ.get(ENV_ENIGMA_HOME)
    if override:
        return Path(override).expanduser()
    base = home if home is not None else Path.home()
    return base / ".enigma"


def storage_root_for(
    mode: EnvironmentMode,
    *,
    scenario: str | None = None,
    home: Path | None = None,
) -> Path:
    """Return the storage root for Demo, Private, or Shadow.

    Defaults encode ``~/.enigma/private``, ``~/.enigma/demo/<scenario>``,
    and ``~/.enigma/shadow``. Override with ``ENIGMA_PRIVATE_STORAGE_ROOT``,
    ``ENIGMA_DEMO_STORAGE_ROOT`` (parent of per-scenario dirs), or
    ``ENIGMA_SHADOW_STORAGE_ROOT``.
    """
    if mode is EnvironmentMode.PRIVATE:
        override = os.environ.get(ENV_PRIVATE_ROOT)
        if override:
            return Path(override).expanduser()
        return default_enigma_home(home=home) / "private"

    if mode is EnvironmentMode.SHADOW:
        override = os.environ.get(ENV_SHADOW_ROOT)
        if override:
            return Path(override).expanduser()
        return default_enigma_home(home=home) / "shadow"

    if not scenario:
        raise ValueError("scenario id is required for DEMO storage roots")
    demo_override = os.environ.get(ENV_DEMO_ROOT)
    if demo_override:
        return Path(demo_override).expanduser() / scenario
    return default_enigma_home(home=home) / "demo" / scenario


def is_real_data_source(source: object) -> bool:
    """True if ``source`` is a production ingestion connector or bridge client."""
    module = type(source).__module__
    return any(
        module == prefix.rstrip(".") or module.startswith(prefix)
        for prefix in _REAL_SOURCE_MODULE_PREFIXES
    )


def assert_source_allowed_for_mode(mode: EnvironmentMode, source: object) -> None:
    """Enforce ``REAL SOURCE ACCESS = IMPOSSIBLE`` under Demo Mode."""
    if mode is EnvironmentMode.DEMO and is_real_data_source(source):
        name = type(source).__qualname__
        raise RealSourceAccessError(
            f"REAL SOURCE ACCESS = IMPOSSIBLE in DEMO; refused {name} "
            f"from {type(source).__module__}"
        )


def refuse_demo_data_migration(
    *,
    source_mode: EnvironmentMode | None = None,
    target_mode: EnvironmentMode = EnvironmentMode.SHADOW,
    source_root: Path | None = None,
    target_root: Path | None = None,
    operation: str = "migrate",
) -> NoReturn:
    """Hard-refuse Demo→Shadow / Demo→Private storage or secret migration.

    There is no successful path. Any call raises ([ADR-008]).
    """
    if target_mode not in (EnvironmentMode.SHADOW, EnvironmentMode.PRIVATE):
        raise DemoDataMigrationError(
            "refuse_demo_data_migration only applies to shadow|private "
            f"targets; got {target_mode.value!r}"
        )
    detail = ""
    if source_root is not None or target_root is not None:
        detail = f" ({source_root!s} → {target_root!s})"
    source = source_mode.value if source_mode is not None else "demo?"
    raise DemoDataMigrationError(
        f"NO DEMO→{target_mode.value.upper()} MIGRATION: refused "
        f"{operation!r} {source}→{target_mode.value}{detail}. "
        "Shadow Mode requires a fresh private DB; demo data must not be "
        "copied, linked, or remapped."
    )


@dataclass
class SecretNamespace:
    """Isolated secret bag per environment — Demo never holds private credentials."""

    _values: dict[str, str] = field(default_factory=dict, repr=False)

    def get(self, key: str) -> str | None:
        return self._values.get(key)

    def set(self, key: str, value: str) -> None:
        self._values[key] = value

    def keys(self) -> frozenset[str]:
        return frozenset(self._values)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key in self._values


@dataclass
class DemoEnvironment:
    """Demo runtime: synthetic sources only, separate storage, injectable clock.

    Full lifecycle (load / reset / advance) lands in later D* tickets.
    """

    scenario: str
    mode: EnvironmentMode = EnvironmentMode.DEMO
    clock: Clock = field(default_factory=SimulationClock)
    secrets: SecretNamespace = field(default_factory=SecretNamespace)
    gmail_credentials: None = None
    apple_bridge: None = None
    _sources: list[Any] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.mode is not EnvironmentMode.DEMO:
            raise ValueError("DemoEnvironment requires EnvironmentMode.DEMO")
        leaked = PRIVATE_CREDENTIAL_KEYS.intersection(self.secrets.keys())
        if leaked:
            raise RealSourceAccessError(
                f"Demo secret namespace must not contain private credentials: {sorted(leaked)}"
            )

    @property
    def storage_root(self) -> Path:
        return storage_root_for(self.mode, scenario=self.scenario)

    @property
    def banner_text(self) -> str:
        return DEMO_BANNER_TEXT

    def register_source(self, source: object) -> None:
        """Register a source; real connectors raise :class:`RealSourceAccessError`."""
        assert_source_allowed_for_mode(self.mode, source)
        self._sources.append(source)

    @property
    def sources(self) -> tuple[Any, ...]:
        return tuple(self._sources)


@dataclass
class PrivateEnvironment:
    """Private runtime: real connectors, wall clock, private secret namespace."""

    mode: EnvironmentMode = EnvironmentMode.PRIVATE
    clock: Clock = field(default_factory=SystemClock)
    secrets: SecretNamespace = field(default_factory=SecretNamespace)
    _sources: list[Any] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.mode is not EnvironmentMode.PRIVATE:
            raise ValueError("PrivateEnvironment requires EnvironmentMode.PRIVATE")

    @property
    def storage_root(self) -> Path:
        return storage_root_for(self.mode)

    def register_source(self, source: object) -> None:
        self._sources.append(source)

    @property
    def sources(self) -> tuple[Any, ...]:
        return tuple(self._sources)


@dataclass
class ShadowEnvironment:
    """Shadow runtime: real sources, wall clock, fresh Shadow storage, quiet UI.

    Notification suppression and attention-log persistence land in S03–S04.
    Demo→Shadow migration is structurally impossible ([ADR-008]).
    """

    mode: EnvironmentMode = EnvironmentMode.SHADOW
    clock: Clock = field(default_factory=SystemClock)
    secrets: SecretNamespace = field(default_factory=SecretNamespace)
    notifications_suppressed: bool = True
    _sources: list[Any] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.mode is not EnvironmentMode.SHADOW:
            raise ValueError("ShadowEnvironment requires EnvironmentMode.SHADOW")
        if not self.notifications_suppressed:
            raise ValueError("ShadowEnvironment requires notifications_suppressed=True")

    @property
    def storage_root(self) -> Path:
        return storage_root_for(self.mode)

    @property
    def banner_text(self) -> str:
        return SHADOW_BANNER_TEXT

    def register_source(self, source: object) -> None:
        assert_source_allowed_for_mode(self.mode, source)
        self._sources.append(source)

    @property
    def sources(self) -> tuple[Any, ...]:
        return tuple(self._sources)

    def migrate_from_demo(self, demo_root: Path) -> NoReturn:
        """Always raise — Demo artefacts must never enter Shadow storage."""
        refuse_demo_data_migration(
            operation="ShadowEnvironment.migrate_from_demo",
            source_mode=EnvironmentMode.DEMO,
            target_mode=EnvironmentMode.SHADOW,
            source_root=demo_root,
            target_root=self.storage_root,
        )


def build_environment(
    mode: EnvironmentMode | None = None,
    *,
    scenario: str | None = None,
    clock: Clock | None = None,
) -> DemoEnvironment | PrivateEnvironment | ShadowEnvironment:
    """Construct the active environment from mode (default: env var / private)."""
    resolved = mode if mode is not None else environment_mode_from_env()
    if resolved is EnvironmentMode.DEMO:
        if not scenario:
            scenario = os.environ.get("ENIGMA_DEMO_SCENARIO", "alex-v1")
        return DemoEnvironment(
            scenario=scenario,
            clock=clock if clock is not None else SimulationClock(),
        )
    if resolved is EnvironmentMode.SHADOW:
        return ShadowEnvironment(clock=clock if clock is not None else SystemClock())
    return PrivateEnvironment(clock=clock if clock is not None else SystemClock())
