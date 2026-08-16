"""Local-only SQLite database settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_DATABASE_URL = "ENIGMA_DATABASE_URL"
DEFAULT_DIR_NAME = "personal-enigma"
DEFAULT_DB_FILENAME = "private.db"


def default_database_path() -> Path:
    """Return the default on-disk path for the private SQLite file."""
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        root = Path(xdg)
    else:
        root = Path.home() / ".local" / "share"
    return root / DEFAULT_DIR_NAME / DEFAULT_DB_FILENAME


def assert_local_sqlite_url(url: str) -> str:
    """Reject non-SQLite or host-qualified database URLs.

    Enigma's private DB must stay local. Only ``sqlite:`` schemes are allowed;
    SQLAlchemy's SQLite dialect does not open a network listener.
    """
    normalized = url.strip()
    lower = normalized.lower()
    if not lower.startswith("sqlite:"):
        raise ValueError(
            f"Only local sqlite URLs are allowed for the private DB; got {url!r}"
        )
    # After ``sqlite:`` expect ``//`` then a path (``/…``) or ``:memory:``.
    # Reject shapes like ``sqlite:relative.db`` that omit ``//`` (except ``:memory:``).
    rest = normalized[len("sqlite:") :]
    if rest.lower() == ":memory:" or rest.lower().startswith(":memory:?"):
        return normalized
    if not rest.startswith("//"):
        raise ValueError(
            f"SQLite URLs must use sqlite:///… or sqlite:///:memory:; got {url!r}"
        )
    after_slashes = rest[2:]
    if not (
        after_slashes.startswith("/")
        or after_slashes.lower().startswith(":memory:")
    ):
        raise ValueError(
            f"Networked or host-qualified sqlite URLs are forbidden; got {url!r}"
        )
    return normalized


def path_to_sqlite_url(path: Path) -> str:
    """Build a SQLAlchemy SQLite URL for an absolute or relative file path."""
    resolved = path.expanduser().resolve()
    return f"sqlite:///{resolved}"


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """Resolved connection settings for the private store."""

    url: str

    @classmethod
    def from_env(cls, *, fallback_path: Path | None = None) -> DatabaseSettings:
        raw = os.environ.get(ENV_DATABASE_URL)
        if raw:
            return cls(url=assert_local_sqlite_url(raw))
        path = fallback_path if fallback_path is not None else default_database_path()
        return cls(url=assert_local_sqlite_url(path_to_sqlite_url(path)))
