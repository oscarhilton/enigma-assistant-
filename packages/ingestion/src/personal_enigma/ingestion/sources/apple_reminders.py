"""Apple Reminders DataSource adapter — owned by ticket M09."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

import httpx

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

        payload = await self._get_reminders_changes(params)
        authorised = bool(payload.get("authorised", False))
        if not authorised:
            # Permission denied: Core keeps running with an empty batch.
            return ChangeBatch(items=[], next_cursor=None, exhausted=True)

        items: list[dict[str, Any]] = []
        for raw in payload.get("items") or []:
            if not isinstance(raw, Mapping):
                continue
            reminder = PrivateReminder.model_validate({**raw, "provider": "apple_reminders"})
            items.append(reminder.model_dump(mode="json"))

        next_cursor = self._parse_cursor(payload.get("next_cursor"))
        exhausted = bool(payload.get("exhausted", True))
        return ChangeBatch(items=items, next_cursor=next_cursor, exhausted=exhausted)

    async def _get_reminders_changes(self, params: dict[str, str]) -> dict[str, Any]:
        path = "/reminders/changes"
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
            source=source if isinstance(source, str) else "apple_reminders",
        )
