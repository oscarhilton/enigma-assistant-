"""Encrypted audit metadata store."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from personal_enigma.api.storage.crypto import CryptoError, decrypt_blob, encrypt_blob


class AuditStore:
    """Privacy-safe egress audit records encrypted under the AUDIT KEY."""

    def __init__(self, root: Path, *, audit_key: bytes) -> None:
        self._root = root
        self._audit_key = audit_key
        self._root.mkdir(parents=True, exist_ok=True)

    def append_record(
        self,
        *,
        event_type: str,
        payload_hash: str,
        field_summary: dict[str, object],
    ) -> str:
        """Persist an encrypted audit record; returns record id."""
        record_id = uuid4().hex
        body = json.dumps(
            {
                "id": record_id,
                "event_type": event_type,
                "payload_hash": payload_hash,
                "field_summary": field_summary,
                "recorded_at": datetime.now(tz=UTC).isoformat(),
            },
            sort_keys=True,
        ).encode("utf-8")
        path = self._root / f"{record_id}.enc"
        path.write_bytes(encrypt_blob(self._audit_key, body))
        return record_id

    def read_record(self, record_id: str) -> dict[str, object]:
        path = self._root / f"{record_id}.enc"
        if not path.exists():
            raise FileNotFoundError(record_id)
        try:
            raw = decrypt_blob(self._audit_key, path.read_bytes())
        except CryptoError as exc:
            raise ValueError(f"Failed to decrypt audit record {record_id}") from exc
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("Audit record must be a JSON object")
        return parsed
