"""Alembic migration helpers for the private SQLite database."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

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
