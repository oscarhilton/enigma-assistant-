"""Gmail persistence guard — SEC-04 hard precondition.

When ``persistence_backend == legacy_plaintext`` (legacy ``private.db`` /
``personal_enigma.api.db``), Gmail ingestion is **refused** with no warning,
fallback, or dev exception during SEC-04 evaluation. Live sync requires
``encrypted_vault`` persistence only.
"""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path

ENV_DATABASE_URL = "ENIGMA_DATABASE_URL"
ENV_PERSISTENCE_BACKEND = "ENIGMA_PERSISTENCE_BACKEND"
LEGACY_DIR_NAME = "personal-enigma"
LEGACY_DB_FILENAME = "private.db"
VAULT_DB_FILENAME = "vault.db"


class PersistenceBackend(StrEnum):
    """Resolved private persistence tier for Gmail ingestion guards."""

    LEGACY_PLAINTEXT = "legacy_plaintext"
    ENCRYPTED_VAULT = "encrypted_vault"


class LegacyPrivateStoreError(RuntimeError):
    """Gmail ingestion refused: persistence backend is legacy_plaintext."""


def default_legacy_database_path() -> Path:
    """Default on-disk path for legacy ``personal_enigma.api.db`` store.

    Mirrors ``personal_enigma.api.db.config.default_database_path``:
    ``$XDG_DATA_HOME/personal-enigma/private.db`` or
    ``~/.local/share/personal-enigma/private.db``.
    """
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        root = Path(xdg)
    else:
        root = Path.home() / ".local" / "share"
    return root / LEGACY_DIR_NAME / LEGACY_DB_FILENAME


def sqlite_url_to_path(url: str) -> Path:
    """Extract the filesystem path from a local SQLite SQLAlchemy URL."""
    normalized = url.strip()
    lower = normalized.lower()
    if not lower.startswith("sqlite:"):
        raise ValueError(f"Expected sqlite URL, got {url!r}")
    rest = normalized[len("sqlite:") :]
    if rest.lower().startswith(":memory:"):
        raise ValueError("In-memory SQLite is not a Gmail persistence target")
    if not rest.startswith("//"):
        raise ValueError(f"Invalid sqlite URL: {url!r}")
    file_part = rest[2:].split("?", 1)[0]
    return Path(file_part).expanduser().resolve()


def is_legacy_private_db_path(path: Path) -> bool:
    """Return True when ``path`` is the legacy plaintext private.db store."""
    return path.name == LEGACY_DB_FILENAME


def resolve_gmail_persistence_path(
    *,
    database_url: str | None = None,
    database_path: Path | None = None,
) -> Path:
    """Resolve the SQLite file Gmail sync would persist to."""
    if database_path is not None:
        return database_path.expanduser().resolve()
    if database_url is not None:
        return sqlite_url_to_path(database_url)
    env_url = os.environ.get(ENV_DATABASE_URL)
    if env_url:
        return sqlite_url_to_path(env_url)
    return default_legacy_database_path().expanduser().resolve()


def resolve_persistence_backend(
    *,
    database_url: str | None = None,
    database_path: Path | None = None,
    persistence_backend: PersistenceBackend | str | None = None,
) -> PersistenceBackend:
    """Resolve the active persistence backend for Gmail ingestion guards."""
    if persistence_backend is not None:
        return PersistenceBackend(persistence_backend)
    env_backend = os.environ.get(ENV_PERSISTENCE_BACKEND)
    if env_backend:
        return PersistenceBackend(env_backend.strip())
    target = resolve_gmail_persistence_path(
        database_url=database_url,
        database_path=database_path,
    )
    if target.name == VAULT_DB_FILENAME:
        return PersistenceBackend.ENCRYPTED_VAULT
    if is_legacy_private_db_path(target):
        return PersistenceBackend.LEGACY_PLAINTEXT
    # Unknown SQLite targets default to legacy_plaintext — refuse Gmail until explicit vault.
    return PersistenceBackend.LEGACY_PLAINTEXT


def assert_gmail_encrypted_vault_persistence(
    *,
    database_url: str | None = None,
    database_path: Path | None = None,
    persistence_backend: PersistenceBackend | str | None = None,
) -> None:
    """Refuse Gmail init/sync when persistence backend is legacy_plaintext."""
    backend = resolve_persistence_backend(
        database_url=database_url,
        database_path=database_path,
        persistence_backend=persistence_backend,
    )
    if backend == PersistenceBackend.LEGACY_PLAINTEXT:
        target = resolve_gmail_persistence_path(
            database_url=database_url,
            database_path=database_path,
        )
        raise LegacyPrivateStoreError(
            "Gmail ingestion refused: persistence_backend is legacy_plaintext "
            f"(target {target}). SEC-04 requires encrypted_vault storage "
            "(vault.db + blobs/ under ~/.enigma/private/). "
            "No fallback or dev exception is permitted during SEC-04 evaluation."
        )
