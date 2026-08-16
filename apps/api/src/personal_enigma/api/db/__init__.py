"""Local private SQLite persistence for Enigma Core.

The database is file-backed (or in-memory for tests) and must never be exposed
over the network. See ``README.md`` in this package for migration docs.
"""

from personal_enigma.api.db.config import DatabaseSettings, assert_local_sqlite_url
from personal_enigma.api.db.engine import create_db_engine, make_session_factory
from personal_enigma.api.db.models import Base, IngestedRecordRow, ObligationRow, SyncCursorRow
from personal_enigma.api.db.store import PrivateStore, open_store

__all__ = [
    "Base",
    "DatabaseSettings",
    "IngestedRecordRow",
    "ObligationRow",
    "PrivateStore",
    "SyncCursorRow",
    "assert_local_sqlite_url",
    "create_db_engine",
    "make_session_factory",
    "open_store",
]
