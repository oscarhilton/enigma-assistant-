"""Apple Notes DataSource adapter — owned by ticket M13."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

import httpx

from personal_enigma.domain import PrivateNote
from personal_enigma.ingestion.bridge_client import AppleBridgeClient, AppleBridgeError
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor

# Capability quality for Apple Notes (ADR-004).
NOTES_CAPABILITY_QUALITY = "best_effort"


class AppleNotesSource:
    """Fetch Apple Notes changes via the local bridge (`GET /notes/changes`).

    Bridge access is best-effort Apple Events / scripting (never Notes SQLite).
    Mapped records are ``PrivateNote`` with ``provider="apple_notes"``.
    Default remote privacy is HIGH; wholesale bodies are not remote-safe.
    """

    source_name = "apple_notes"
    capability_quality = NOTES_CAPABILITY_QUALITY

    def __init__(self, client: AppleBridgeClient) -> None:
        self._client = client

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        params: dict[str, str] = {}
        if cursor and cursor.value:
            params["cursor"] = cursor.value

        payload = await self._get_notes_changes(params)
        authorised = bool(payload.get("authorised", False))
        if not authorised:
            # Opt-in / automation denied: Core keeps running with an empty batch.
            return ChangeBatch(items=[], next_cursor=None, exhausted=True)

        items: list[dict[str, Any]] = []
        for raw in payload.get("items") or []:
            if not isinstance(raw, Mapping):
                continue
            note = PrivateNote.model_validate({**raw, "provider": "apple_notes"})
            items.append(self._enrich_note_dump(note))

        next_cursor = self._parse_cursor(payload.get("next_cursor"))
        exhausted = bool(payload.get("exhausted", True))
        return ChangeBatch(items=items, next_cursor=next_cursor, exhausted=exhausted)

    def _enrich_note_dump(self, note: PrivateNote) -> dict[str, Any]:
        """Annotate metadata; never mark wholesale bodies remote-safe."""
        data = note.model_dump(mode="json")
        metadata = dict(data.get("metadata") or {})
        metadata.setdefault("quality", self.capability_quality)
        metadata.setdefault("remote_privacy_default", "high")
        # Local relevance stubs live in privacy.notes_policy; ingestion never ships body.
        metadata.setdefault("wholesale_body_remote_safe", "false")
        metadata.setdefault("local_relevance_passages", "0")
        data["metadata"] = metadata
        return data

    async def _get_notes_changes(self, params: dict[str, str]) -> dict[str, Any]:
        path = "/notes/changes"
        if params:
            path = f"{path}?{urlencode(params)}"

        # Reuse AppleBridgeClient transport / auth without extending M07's public API.
        headers = self._client._headers()  # noqa: SLF001
        async with self._client._client() as http:  # noqa: SLF001
            try:
                response = await http.get(path, headers=headers)
            except httpx.HTTPError as exc:
                raise AppleBridgeError(f"Apple Bridge request failed: {exc}") from exc

        if response.status_code == 401:
            raise AppleBridgeError("Apple Bridge rejected bearer token")
        if response.status_code >= 400:
            raise AppleBridgeError(
                f"Apple Bridge returned HTTP {response.status_code}: {response.text}"
            )

        body: Any = response.json()
        if not isinstance(body, dict):
            raise AppleBridgeError("Apple Bridge returned a non-object JSON body")
        return body

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
