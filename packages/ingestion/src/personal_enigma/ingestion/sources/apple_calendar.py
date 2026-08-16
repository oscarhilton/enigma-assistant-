"""Apple Calendar DataSource adapter — owned by ticket M08."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import ValidationError

from personal_enigma.domain import PrivateCalendarEvent
from personal_enigma.ingestion.bridge_client import AppleBridgeClient, AppleBridgeError
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor


class AppleCalendarSource:
    """Fetch Apple Calendar changes via the local bridge (`GET /calendar/changes`)."""

    source_name = "apple_calendar"

    def __init__(
        self,
        client: AppleBridgeClient,
        selected_calendar_ids: Sequence[str] | None = None,
    ) -> None:
        self._client = client
        self._selected_calendar_ids = [cid for cid in (selected_calendar_ids or []) if cid]

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        params: dict[str, str] = {}
        if cursor and cursor.value:
            params["cursor"] = cursor.value
        if self._selected_calendar_ids:
            params["calendar_ids"] = ",".join(self._selected_calendar_ids)

        payload = await self._client.get_json("/calendar/changes", params=params or None)
        authorised = bool(payload.get("authorised", False))
        if not authorised:
            return ChangeBatch(items=[], next_cursor=None, exhausted=True)

        items: list[dict[str, Any]] = []
        for raw in payload.get("items") or []:
            if not isinstance(raw, Mapping):
                continue
            try:
                event = PrivateCalendarEvent.model_validate(
                    {**dict(raw), "provider": "apple_calendar"}
                )
            except ValidationError as exc:
                raise AppleBridgeError(
                    "Apple Bridge returned an invalid calendar payload"
                ) from exc
            items.append(event.model_dump(mode="json"))

        next_cursor = self._parse_cursor(payload.get("next_cursor"))
        exhausted = bool(payload.get("exhausted", True))
        return ChangeBatch(items=items, next_cursor=next_cursor, exhausted=exhausted)

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
            source=source if isinstance(source, str) else "apple_calendar",
        )
