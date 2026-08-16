"""Engine and session factory for the local private database."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from personal_enigma.api.db.config import DatabaseSettings, assert_local_sqlite_url


def _ensure_parent_dir(url: str) -> None:
    """Create the parent directory for file-backed SQLite URLs."""
    if ":memory:" in url:
        return
    # sqlite:///absolute/or/relative/path
    if not url.startswith("sqlite:///"):
        return
    raw_path = url.removeprefix("sqlite:///")
    # SQLAlchemy may append ?query; strip it.
    path_part = raw_path.split("?", 1)[0]
    if not path_part or path_part == ":memory:":
        return
    path = Path(path_part)
    if path.parent and str(path.parent) not in {"", "."}:
        path.parent.mkdir(parents=True, exist_ok=True)


def create_db_engine(settings: DatabaseSettings | None = None, *, url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine bound to a local SQLite database."""
    if url is not None:
        resolved = assert_local_sqlite_url(url)
    elif settings is not None:
        resolved = assert_local_sqlite_url(settings.url)
    else:
        resolved = DatabaseSettings.from_env().url

    _ensure_parent_dir(resolved)
    engine = create_engine(
        resolved,
        connect_args={"check_same_thread": False},
        # Local file DB only — no pool that implies a remote server.
        pool_pre_ping=False,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a session factory bound to ``engine``."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
