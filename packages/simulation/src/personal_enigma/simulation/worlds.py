"""Product worlds — Alex Lab vs My Enigma (P01 / ADR-040).

Same Enigma, two isolated ``WorldHandle``s. Never share storage roots or HMAC keys
([ADR-005](../../../../../docs/adr/005-demo-private-storage-roots.md)).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Final

from personal_enigma.simulation.checkpoints import reset_demo_storage
from personal_enigma.simulation.clock import Clock, SimulationClock, SystemClock
from personal_enigma.simulation.engine import assert_demo_storage_root
from personal_enigma.simulation.environment import (
    DemoEnvironment,
    EnvironmentMode,
    PrivateEnvironment,
    environment_mode_from_env,
    storage_root_for,
)

ENV_ACTIVE_WORLD: Final[str] = "ENIGMA_ACTIVE_WORLD"
HMAC_KEY_FILENAME: Final[str] = "hmac.key"
SECRETS_DIRNAME: Final[str] = "secrets"
HMAC_KEY_BYTES: Final[int] = 32
PERSON_TOKEN_PREFIX: Final[str] = "PERSON_"


class WorldId(StrEnum):
    """Product-facing world — labels over EnvironmentMode, not a new storage identity."""

    ALEX_LAB = "alex_lab"
    MY_ENIGMA = "my_enigma"


class WorldIsolationError(RuntimeError):
    """Raised when Alex Lab and My Enigma would share storage, keys, or identities."""


WORLD_LABELS: Final[dict[WorldId, str]] = {
    WorldId.ALEX_LAB: "Alex Lab",
    WorldId.MY_ENIGMA: "My Enigma",
}

WORLD_SUBTITLES: Final[dict[WorldId, str]] = {
    WorldId.ALEX_LAB: "Synthetic world · controlled clock · resettable",
    WorldId.MY_ENIGMA: "Private world · real clock · persistent",
}


def environment_mode_for_world(world: WorldId) -> EnvironmentMode:
    """Map a product world onto the existing environment mode."""
    if world is WorldId.ALEX_LAB:
        return EnvironmentMode.DEMO
    return EnvironmentMode.PRIVATE


def world_id_for_environment_mode(mode: EnvironmentMode) -> WorldId:
    """Map Demo → Alex Lab; Private (and any other non-demo boot) → My Enigma.

    Shadow is not a product world in P01; a shadow process still defaults the
    switcher to My Enigma rather than inventing a third chrome option.
    """
    if mode is EnvironmentMode.DEMO:
        return WorldId.ALEX_LAB
    return WorldId.MY_ENIGMA


def parse_world_id(value: str | None) -> WorldId:
    """Parse a world id from config/API; empty falls through to env default."""
    if value is None or value.strip() == "":
        return default_world_from_env()
    normalised = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "alex": WorldId.ALEX_LAB,
        "alex_lab": WorldId.ALEX_LAB,
        "demo": WorldId.ALEX_LAB,
        "lab": WorldId.ALEX_LAB,
        "my_enigma": WorldId.MY_ENIGMA,
        "private": WorldId.MY_ENIGMA,
        "enigma": WorldId.MY_ENIGMA,
    }
    if normalised in aliases:
        return aliases[normalised]
    try:
        return WorldId(normalised)
    except ValueError as exc:
        raise ValueError(
            f"Unknown world {value!r}; expected alex_lab|my_enigma"
        ) from exc


def default_world_from_env() -> WorldId:
    """``ENIGMA_ACTIVE_WORLD`` overrides; else ``ENIGMA_ENVIRONMENT_MODE``."""
    explicit = os.environ.get(ENV_ACTIVE_WORLD)
    if explicit and explicit.strip():
        return parse_world_id(explicit)
    return world_id_for_environment_mode(environment_mode_from_env())


def hmac_key_path(root: Path) -> Path:
    return root / SECRETS_DIRNAME / HMAC_KEY_FILENAME


def hmac_fingerprint(key: bytes) -> str:
    """Non-secret handle for tests and API payloads — never the raw key."""
    return "sha256:" + hashlib.sha256(key).hexdigest()[:16]


def person_token_for(key: bytes, email: str) -> str:
    """Opaque PERSON_* token for isolation tests (same shape as identity HMAC)."""
    material = f"email:{email.strip().lower()}"
    digest = hmac.new(key, material.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{PERSON_TOKEN_PREFIX}{digest[:6].upper()}"


def _assert_resolved_under_root(path: Path, root: Path, *, what: str) -> Path:
    resolved = path.expanduser().resolve()
    root_resolved = root.expanduser().resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise WorldIsolationError(
            f"{what} must live under world root {root_resolved}; got {resolved}"
        )
    if resolved.is_symlink():
        raise WorldIsolationError(f"{what} must not be a symlink ({resolved})")
    return resolved


def load_or_create_hmac_key(root: Path) -> bytes:
    """Load ``secrets/hmac.key`` under ``root``, or create a fresh 32-byte key.

    Refuses to follow a key file out of the world root (symlink / alias leak).
    """
    secrets_dir = root / SECRETS_DIRNAME
    secrets_dir.mkdir(parents=True, exist_ok=True)
    path = hmac_key_path(root)
    if path.exists() or path.is_symlink():
        resolved = _assert_resolved_under_root(path, root, what="HMAC key")
        raw = resolved.read_text(encoding="utf-8").strip()
        if not raw:
            raise WorldIsolationError(f"HMAC key at {resolved} is empty")
        try:
            key = bytes.fromhex(raw)
        except ValueError as exc:
            raise WorldIsolationError(f"HMAC key at {resolved} is not hex") from exc
        if len(key) < 16:
            raise WorldIsolationError(f"HMAC key at {resolved} is too short")
        return key

    key = secrets.token_bytes(HMAC_KEY_BYTES)
    path.write_text(key.hex() + "\n", encoding="utf-8")
    path.chmod(0o600)
    _assert_resolved_under_root(path, root, what="HMAC key")
    return key


def assert_private_storage_root(root: Path) -> None:
    """Reject Demo / Shadow roots for My Enigma (ADR-005 / ADR-040)."""
    resolved = root.expanduser().resolve()
    parts = resolved.parts
    for index, part in enumerate(parts[:-1]):
        if part in {".enigma", "enigma"} and parts[index + 1] == "demo":
            raise WorldIsolationError(
                f"My Enigma must not use a Demo storage root (got {resolved})"
            )
        if part in {".enigma", "enigma"} and parts[index + 1] == "shadow":
            raise WorldIsolationError(
                f"My Enigma must not use a Shadow storage root (got {resolved})"
            )
    if resolved.name in {"demo", "shadow"}:
        raise WorldIsolationError(
            f"My Enigma must not bind to {resolved.name} (got {resolved})"
        )
    if "demo" in parts and resolved.name not in {"private", "enigma.db"}:
        # Per-scenario demo dirs are named after the scenario (e.g. alex-v1).
        if "alex-v1" in parts or resolved.parent.name == "demo":
            raise WorldIsolationError(
                f"My Enigma must not use a Demo storage root (got {resolved})"
            )


def assert_world_storage_root(
    world: WorldId,
    root: Path,
    *,
    scenario: str = "alex-v1",
) -> None:
    """Refuse cross-world storage bindings."""
    if world is WorldId.ALEX_LAB:
        try:
            assert_demo_storage_root(root, scenario_id=scenario)
        except ValueError as exc:
            raise WorldIsolationError(str(exc)) from exc
        return
    assert_private_storage_root(root)


def _paths_overlap(left: Path, right: Path) -> bool:
    a = left.expanduser().resolve()
    b = right.expanduser().resolve()
    return a == b or a in b.parents or b in a.parents


@dataclass
class WorldHandle:
    """Isolated runtime identity for one product world."""

    world: WorldId
    environment: DemoEnvironment | PrivateEnvironment
    scenario: str | None = None
    home: Path | None = None
    _hmac_key: bytes | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        expected = environment_mode_for_world(self.world)
        if self.environment.mode is not expected:
            raise WorldIsolationError(
                f"{self.world.value} requires {expected.value}; "
                f"got {self.environment.mode.value}"
            )
        if self.world is WorldId.ALEX_LAB and not isinstance(
            self.environment.clock, SimulationClock
        ):
            raise WorldIsolationError("Alex Lab requires SimulationClock")
        if self.world is WorldId.MY_ENIGMA and not isinstance(
            self.environment.clock, SystemClock
        ):
            raise WorldIsolationError("My Enigma requires SystemClock")

    @classmethod
    def open(
        cls,
        world: WorldId,
        *,
        scenario: str = "alex-v1",
        home: Path | None = None,
        clock: Clock | None = None,
    ) -> WorldHandle:
        """Construct a handle bound to the world's storage root and clock type."""
        if world is WorldId.ALEX_LAB:
            env = DemoEnvironment(
                scenario=scenario,
                clock=clock if isinstance(clock, SimulationClock) else SimulationClock(),
            )
            return cls(world=world, environment=env, scenario=scenario, home=home)

        env = PrivateEnvironment(
            clock=clock if isinstance(clock, SystemClock) else SystemClock(),
        )
        return cls(world=world, environment=env, scenario=None, home=home)

    @property
    def label(self) -> str:
        return WORLD_LABELS[self.world]

    @property
    def subtitle(self) -> str:
        return WORLD_SUBTITLES[self.world]

    @property
    def mode(self) -> EnvironmentMode:
        return self.environment.mode

    @property
    def storage_root(self) -> Path:
        if self.world is WorldId.ALEX_LAB:
            return storage_root_for(
                EnvironmentMode.DEMO,
                scenario=self.scenario or "alex-v1",
                home=self.home,
            )
        return storage_root_for(EnvironmentMode.PRIVATE, home=self.home)

    @property
    def database_path(self) -> Path:
        return self.storage_root / "enigma.db"

    @property
    def clock(self) -> Clock:
        return self.environment.clock

    @property
    def clock_kind(self) -> str:
        if isinstance(self.clock, SimulationClock):
            return "simulation"
        return "system"

    @property
    def resettable(self) -> bool:
        return self.world is WorldId.ALEX_LAB

    @property
    def persistent(self) -> bool:
        return self.world is WorldId.MY_ENIGMA

    @property
    def hmac_key(self) -> bytes:
        if self._hmac_key is None:
            key = load_or_create_hmac_key(self.storage_root)
            self._bind_secret(key)
            self._hmac_key = key
        return self._hmac_key

    @property
    def hmac_fingerprint(self) -> str:
        return hmac_fingerprint(self.hmac_key)

    def _bind_secret(self, key: bytes) -> None:
        hex_key = key.hex()
        if self.world is WorldId.ALEX_LAB:
            self.environment.secrets.set("DEMO_HMAC_KEY", hex_key)
            leaked = "PRIVATE_HMAC_KEY" in self.environment.secrets
            if leaked:
                raise WorldIsolationError(
                    "Alex Lab secret namespace must not contain PRIVATE_HMAC_KEY"
                )
            return
        self.environment.secrets.set("PRIVATE_HMAC_KEY", hex_key)

    def public_view(self) -> dict[str, object]:
        """JSON-safe world descriptor — no raw HMAC material."""
        return {
            "id": self.world.value,
            "label": self.label,
            "subtitle": self.subtitle,
            "environment_mode": self.mode.value,
            "clock_kind": self.clock_kind,
            "resettable": self.resettable,
            "persistent": self.persistent,
            "storage_root": str(self.storage_root),
            "database_path": str(self.database_path),
            "hmac_fingerprint": self.hmac_fingerprint,
            "scenario": self.scenario,
        }


@dataclass
class WorldRegistry:
    """Process-local pair of isolated worlds plus the active selection."""

    scenario: str = "alex-v1"
    home: Path | None = None
    _handles: dict[WorldId, WorldHandle] = field(init=False, repr=False)
    _active: WorldId = field(init=False)

    def __post_init__(self) -> None:
        self._handles = {
            WorldId.ALEX_LAB: WorldHandle.open(
                WorldId.ALEX_LAB, scenario=self.scenario, home=self.home
            ),
            WorldId.MY_ENIGMA: WorldHandle.open(WorldId.MY_ENIGMA, home=self.home),
        }
        self._active = default_world_from_env()

    @property
    def active_id(self) -> WorldId:
        return self._active

    @property
    def active(self) -> WorldHandle:
        return self._handles[self._active]

    def handle(self, world: WorldId) -> WorldHandle:
        return self._handles[world]

    def switch(self, world: WorldId) -> WorldHandle:
        """Select the active world. Never copies storage or keys."""
        if world not in self._handles:
            raise WorldIsolationError(f"Unknown world {world!r}")
        self.assert_isolated(require_keys=True)
        self._active = world
        return self.active

    def reset(self, world: WorldId | None = None) -> WorldHandle:
        """Reset Alex Lab only. My Enigma is persistent and always refused."""
        target = world if world is not None else self._active
        handle = self._handles[target]
        if not handle.resettable:
            raise WorldIsolationError(
                "My Enigma is persistent; reset is refused (ADR-005 / ADR-040)"
            )
        root = handle.storage_root
        assert_world_storage_root(WorldId.ALEX_LAB, root, scenario=self.scenario)
        private_root = self._handles[WorldId.MY_ENIGMA].storage_root
        if _paths_overlap(root, private_root):
            raise WorldIsolationError("Refusing Alex Lab reset that overlaps My Enigma")
        reset_demo_storage(root)
        # Fresh HMAC after wipe — identities must not survive Demo reset via leftover keys.
        self._handles[WorldId.ALEX_LAB] = WorldHandle.open(
            WorldId.ALEX_LAB, scenario=self.scenario, home=self.home
        )
        _ = self._handles[WorldId.ALEX_LAB].hmac_key
        self.assert_isolated(require_keys=True)
        if self._active is WorldId.ALEX_LAB:
            return self.active
        return self._handles[WorldId.ALEX_LAB]

    def assert_isolated(self, *, require_keys: bool = False) -> None:
        """Hard fence: distinct roots, no nesting, distinct HMAC when loaded."""
        alex = self._handles[WorldId.ALEX_LAB]
        mine = self._handles[WorldId.MY_ENIGMA]
        if alex.mode is mine.mode:
            raise WorldIsolationError("Worlds must not share EnvironmentMode")
        if _paths_overlap(alex.storage_root, mine.storage_root):
            raise WorldIsolationError(
                "Alex Lab and My Enigma must not share or nest storage roots "
                f"({alex.storage_root} vs {mine.storage_root})"
            )
        if alex.database_path.resolve() == mine.database_path.resolve():
            raise WorldIsolationError("Worlds must not share enigma.db")
        if require_keys:
            if alex.hmac_fingerprint == mine.hmac_fingerprint:
                raise WorldIsolationError(
                    "Alex Lab and My Enigma must not share HMAC / PERSON_* keys"
                )
            sample = "maya@example.com"
            if person_token_for(alex.hmac_key, sample) == person_token_for(
                mine.hmac_key, sample
            ):
                raise WorldIsolationError(
                    "Worlds produced identical PERSON_* tokens; HMAC isolation failed"
                )
            if "PRIVATE_HMAC_KEY" in alex.environment.secrets:
                raise WorldIsolationError(
                    "Alex Lab must not hold PRIVATE_HMAC_KEY (ADR-005)"
                )

    def public_view(self) -> dict[str, object]:
        self.assert_isolated(require_keys=True)
        return {
            "active": self._active.value,
            "worlds": [
                self._handles[WorldId.ALEX_LAB].public_view(),
                self._handles[WorldId.MY_ENIGMA].public_view(),
            ],
        }
