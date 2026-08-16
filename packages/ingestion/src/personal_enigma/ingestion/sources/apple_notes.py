"""Apple Notes DataSource adapter — owned by ticket M13."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from personal_enigma.domain import PrivateNote
from personal_enigma.ingestion.bridge_client import AppleBridgeClient, AppleBridgeError
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor

NOTES_CAPABILITY_QUALITY = "best_effort"


class AppleNotesSource:
    """Fetch Apple Notes changes via the local bridge (`GET /notes/changes`)."""

    source_name = "apple_notes"
    capability_quality = NOTES_CAPABILITY_QUALITY

    def __init__(self, client: AppleBridgeClient) -> None:
        self._client = client

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        params: dict[str, str] = {}
        if cursor and cursor.value:
            params["cursor"] = cursor.value

        payload = await self._client.get_json("/notes/changes", params=params or None)
        authorised = bool(payload.get("authorised", False))
        if not authorised:
            return ChangeBatch(items=[], next_cursor=None, exhausted=True)

        items: list[dict[str, Any]] = []
        for raw in payload.get("items") or []:
            if not isinstance(raw, Mapping):
                continue
            try:
                note = PrivateNote.model_validate({**raw, "provider": "apple_notes"})
            except ValidationError as exc:
                raise AppleBridgeError(
                    "Apple Bridge returned an invalid notes payload"
                ) from exc
            items.append(self._enrich_note_dump(note))

        next_cursor = self._parse_cursor(payload.get("next_cursor"))
        exhausted = bool(payload.get("exhausted", True))
        return ChangeBatch(items=items, next_cursor=next_cursor, exhausted=exhausted)

    def _enrich_note_dump(self, note: PrivateNote) -> dict[str, Any]:
        data = note.model_dump(mode="json")
        metadata = dict(data.get("metadata") or {})
        metadata.setdefault("quality", self.capability_quality)
        metadata.setdefault("remote_privacy_default", "high")
        metadata.setdefault("wholesale_body_remote_safe", "false")
        metadata.setdefault("local_relevance_passages", "0")
        data["metadata"] = metadata
        return data

    @staticmethod
    def _parse_cursor(raw: Any) -> SyncCursor | None:
        if not isinstance(raw, Mapping):
            return None
        value = raw.get("value")
        if not isinstance(value, str) or not value:
            return None
        source = raw.get("source")
        return SyncCursor(
            value=value,
            source=source if isinstance(source, str) else "apple_notes",
        )
