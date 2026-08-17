"""Alembic migration helpers for the private SQLite database."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
ALEMBIC_INI = Path(__file__).resolve().parent / "alembic.ini"


def alembic_config(database_url: str) -> Config:
    """Build an Alembic ``Config`` pointed at this package's migration scripts."""
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def upgrade_head(database_url: str) -> None:
    """Apply all migrations up to ``head``."""
    command.upgrade(alembic_config(database_url), "head")


def downgrade_base(database_url: str) -> None:
    """Downgrade all migrations to ``base`` (empty schema aside from alembic_version)."""
    command.downgrade(alembic_config(database_url), "base")


def sqlite_path_from_url(database_url: str) -> Path:
    """Return the filesystem path for a local SQLite URL."""
    resolved = database_url.strip()
    if ":memory:" in resolved:
        raise ValueError("in-memory SQLite URLs have no filesystem path")
    if not resolved.startswith("sqlite:///"):
        raise ValueError(f"expected sqlite:/// URL; got {database_url!r}")
    raw_path = resolved.removeprefix("sqlite:///").split("?", 1)[0]
    return Path(raw_path).expanduser()


def drop_database_files(db_path: Path) -> None:
    """Remove a SQLite file and common WAL sidecars."""
    for candidate in (db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")):
        candidate.unlink(missing_ok=True)


def drop_database(database_url: str, *, engine: Engine | None = None) -> Path:
    """Downgrade Alembic schema when present, then delete the DB file and sidecars."""
    if engine is not None:
        engine.dispose()
    if ":memory:" in database_url:
        return Path(":memory:")
    db_path = sqlite_path_from_url(database_url)
    if db_path.is_file():
        try:
            downgrade_base(database_url)
        except Exception:
            # Non-migrated or partially written demo DB — file delete is enough.
            pass
    drop_database_files(db_path)
    return db_path
