"""Provider-agnostic ingestion interfaces."""

from personal_enigma.ingestion.protocol import ChangeBatch, DataSource, SyncCursor

__all__ = ["ChangeBatch", "DataSource", "SyncCursor"]
