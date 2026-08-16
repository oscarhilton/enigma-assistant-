"""Apple Calendar DataSource adapter — owned by ticket M08."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlencode

import httpx

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

        payload = await self._get_calendar_changes(params)
        authorised = bool(payload.get("authorised", False))
        if not authorised:
            # Permission denied: Core keeps running with an empty batch.
            return ChangeBatch(items=[], next_cursor=None, exhausted=True)

        items: list[dict[str, Any]] = []
        for raw in payload.get("items") or []:
            if not isinstance(raw, Mapping):
                continue
            event = PrivateCalendarEvent.model_validate({**dict(raw), "provider": "apple_calendar"})
            items.append(event.model_dump(mode="json"))

        next_cursor = self._parse_cursor(payload.get("next_cursor"))
        exhausted = bool(payload.get("exhausted", True))
        return ChangeBatch(items=items, next_cursor=next_cursor, exhausted=exhausted)

    async def _get_calendar_changes(self, params: dict[str, str]) -> dict[str, Any]:
        if not self._client.token:
            raise AppleBridgeError("Apple Bridge token is not configured")

        path = "/calendar/changes"
        if params:
            path = f"{path}?{urlencode(params)}"

        headers = {"Authorization": f"Bearer {self._client.token}"}
        async with self._http_client() as http:
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

    def _http_client(self) -> httpx.AsyncClient:
        transport = getattr(self._client, "_transport", None)
        if transport is not None:
            return httpx.AsyncClient(
                base_url=self._client.base_url,
                transport=transport,
                timeout=self._client.timeout,
            )
        if self._client.unix_socket:
            return httpx.AsyncClient(
                base_url="http://localhost",
                transport=httpx.AsyncHTTPTransport(uds=self._client.unix_socket),
                timeout=self._client.timeout,
            )
        return httpx.AsyncClient(base_url=self._client.base_url, timeout=self._client.timeout)

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
