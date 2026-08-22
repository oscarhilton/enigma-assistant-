"""Private vault directory layout under ``ENIGMA_HOME/private/``."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from personal_enigma.simulation import EnvironmentMode, storage_root_for

VAULT_DB_FILENAME = "vault.db"
BLOBS_DIRNAME = "blobs"
AUDIT_DIRNAME = "audit"
CONFIG_FILENAME = "config.json"
WRAPPED_KEYS_FILENAME = "wrapped_keys.enc"

DEFAULT_CONFIG: dict[str, object] = {
    "version": 1,
    "retention": {
        "raw_email_blob_days": 7,
        "resolved_obligation_days": 90,
    },
    "features": {
        "remote_inference_enabled": False,
    },
}


@dataclass(frozen=True, slots=True)
class VaultPaths:
    """Resolved on-disk paths for a Private vault root."""

    root: Path

    @property
    def vault_db(self) -> Path:
        return self.root / VAULT_DB_FILENAME

    @property
    def blobs(self) -> Path:
        return self.root / BLOBS_DIRNAME

    @property
    def audit(self) -> Path:
        return self.root / AUDIT_DIRNAME

    @property
    def config(self) -> Path:
        return self.root / CONFIG_FILENAME

    @property
    def wrapped_keys(self) -> Path:
        return self.root / WRAPPED_KEYS_FILENAME

    def sidecar_paths(self) -> tuple[Path, ...]:
        """WAL / SHM / journal sidecars for ``vault.db``."""
        base = self.vault_db
        return (
            Path(f"{base}-wal"),
            Path(f"{base}-shm"),
            Path(f"{base}-journal"),
        )


def default_vault_paths(*, root: Path | None = None) -> VaultPaths:
    """Return vault paths for Private mode (``~/.enigma/private`` by default)."""
    resolved = root if root is not None else storage_root_for(EnvironmentMode.PRIVATE)
    return VaultPaths(root=resolved)


def ensure_vault_layout(paths: VaultPaths) -> None:
    """Create vault directories and non-secret ``config.json`` if missing."""
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.blobs.mkdir(parents=True, exist_ok=True)
    paths.audit.mkdir(parents=True, exist_ok=True)
    if not paths.config.exists():
        paths.config.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
