"""Worker access to the local private SQLite store.

Schema and Alembic migrations are owned by ``personal_enigma.api.db``.
Worker processes open the same on-disk database file (never a remote host).
"""

from __future__ import annotations

from pathlib import Path

from personal_enigma.api.db import (
    DatabaseSettings,
    PrivateStore,
    assert_local_sqlite_url,
    open_store,
)
from personal_enigma.api.db.config import default_database_path, path_to_sqlite_url
from personal_enigma.api.db.migrate import downgrade_base, upgrade_head


def worker_database_settings(*, path: Path | None = None) -> DatabaseSettings:
    """Resolve DB settings for worker jobs (env or default local file)."""
    return DatabaseSettings.from_env(fallback_path=path)


def open_worker_store(
    *,
    path: Path | None = None,
    url: str | None = None,
    create_schema: bool = False,
) -> PrivateStore:
    """Open the private store for ingestion / attention worker use."""
    if url is not None:
        return open_store(url=url, create_schema=create_schema)
    settings = worker_database_settings(path=path)
    return open_store(settings, create_schema=create_schema)


def migrate_worker_db(*, path: Path | None = None, url: str | None = None) -> str:
    """Apply Alembic migrations to the worker's private DB; return the URL used."""
    if url is not None:
        resolved = assert_local_sqlite_url(url)
    else:
        settings = worker_database_settings(path=path)
        resolved = settings.url
    if resolved.startswith("sqlite:///") and ":memory:" not in resolved:
        file_path = Path(resolved.removeprefix("sqlite:///").split("?", 1)[0])
        file_path.parent.mkdir(parents=True, exist_ok=True)
    upgrade_head(resolved)
    return resolved


__all__ = [
    "DatabaseSettings",
    "PrivateStore",
    "assert_local_sqlite_url",
    "default_database_path",
    "downgrade_base",
    "migrate_worker_db",
    "open_store",
    "open_worker_store",
    "path_to_sqlite_url",
    "upgrade_head",
    "worker_database_settings",
]
