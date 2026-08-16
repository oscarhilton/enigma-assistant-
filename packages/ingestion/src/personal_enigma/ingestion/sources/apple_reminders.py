"""Apple Reminders DataSource adapter — owned by ticket M09."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from personal_enigma.domain import PrivateReminder
from personal_enigma.ingestion.bridge_client import AppleBridgeClient, AppleBridgeError
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor

# Attention engine kind for ingested Apple Reminders (see packages/attention).
# Explicit reminders are first-class intent signals — stronger than email inference.
EXPLICIT_REMINDER_INTENT_SIGNAL = "explicit_reminder"


class AppleReminderSource:
    """Fetch Apple Reminders changes via the local bridge (`GET /reminders/changes`).

    Bridge MVP defaults return incomplete reminders with due dates, mapped to
    ``PrivateReminder`` with ``provider="apple_reminders"``. These feed the
    attention engine as ``EXPLICIT_REMINDER`` intent signals.
    """

    source_name = "apple_reminders"
    intent_signal = EXPLICIT_REMINDER_INTENT_SIGNAL

    def __init__(self, client: AppleBridgeClient) -> None:
        self._client = client

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        params: dict[str, str] = {}
        if cursor and cursor.value:
            params["cursor"] = cursor.value

        payload = await self._client.get_json("/reminders/changes", params=params or None)
        authorised = bool(payload.get("authorised", False))
        if not authorised:
            # Permission denied: Core keeps running with an empty batch.
            return ChangeBatch(items=[], next_cursor=None, exhausted=True)

        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raw_items = []

        items: list[dict[str, Any]] = []
        for raw in raw_items:
            if not isinstance(raw, Mapping):
                continue
            try:
                reminder = PrivateReminder.model_validate(
                    {**raw, "provider": "apple_reminders"}
                )
            except ValidationError as exc:
                raise AppleBridgeError(
                    "Apple Bridge returned an invalid reminder payload"
                ) from exc
            items.append(reminder.model_dump(mode="json"))

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
            source=source if isinstance(source, str) else "apple_reminders",
        )
