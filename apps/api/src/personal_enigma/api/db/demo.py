"""Demo-scoped SQLite database paths and reset helpers (ADR-005)."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.engine import Engine

from personal_enigma.api.db.config import (
    ENV_DATABASE_URL,
    assert_local_sqlite_url,
    path_to_sqlite_url,
)
from personal_enigma.api.db.migrate import drop_database, sqlite_path_from_url
from personal_enigma.simulation import EnvironmentMode, storage_root_for

DEFAULT_DEMO_DB_FILENAME = "enigma.db"


def demo_database_path(*, scenario: str) -> Path:
    """Return the demo SQLite file for ``scenario`` under the Demo storage root."""
    return storage_root_for(EnvironmentMode.DEMO, scenario=scenario) / DEFAULT_DEMO_DB_FILENAME


def assert_demo_database_url(url: str, *, scenario: str) -> str:
    """Refuse Demo DB URLs outside the active scenario Demo root (ADR-005)."""
    resolved = assert_local_sqlite_url(url)
    if ":memory:" in resolved:
        return resolved
    db_path = sqlite_path_from_url(resolved)
    demo_root = storage_root_for(EnvironmentMode.DEMO, scenario=scenario).resolve()
    try:
        db_path.resolve().relative_to(demo_root)
    except ValueError as exc:
        raise ValueError(
            "Demo database URL must live under the active scenario Demo storage "
            f"root ({demo_root}); got {db_path}"
        ) from exc
    return resolved


def resolve_demo_database_url(*, scenario: str) -> str:
    """Resolve the SQLite URL for Demo persistence for ``scenario``."""
    raw = os.environ.get(ENV_DATABASE_URL)
    if raw:
        return assert_demo_database_url(raw, scenario=scenario)
    return path_to_sqlite_url(demo_database_path(scenario=scenario))


def drop_demo_database(
    *,
    scenario: str,
    engine: Engine | None = None,
) -> Path:
    """Drop the Demo SQLite file (Alembic schema + WAL sidecars) for ``scenario``.

    Always removes the canonical ``enigma.db`` under the scenario Demo root.
    When ``ENIGMA_DATABASE_URL`` points at a second file under that root, it is
    dropped too. URLs outside the Demo root are ignored (ADR-005).
    """
    canonical = demo_database_path(scenario=scenario)
    urls: list[str] = [path_to_sqlite_url(canonical)]
    raw = os.environ.get(ENV_DATABASE_URL)
    if raw:
        try:
            configured = assert_demo_database_url(raw, scenario=scenario)
            if configured not in urls:
                urls.append(configured)
        except ValueError:
            pass
    for index, url in enumerate(urls):
        drop_database(url, engine=engine if index == 0 else None)
    return canonical


__all__ = [
    "DEFAULT_DEMO_DB_FILENAME",
    "assert_demo_database_url",
    "demo_database_path",
    "drop_demo_database",
    "resolve_demo_database_url",
]
