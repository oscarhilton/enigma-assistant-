"""Apple Contacts DataSource adapter — owned by ticket M10."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx

from personal_enigma.domain import PrivatePerson
from personal_enigma.ingestion.bridge_client import AppleBridgeClient, AppleBridgeError
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor


class AppleContactsSource:
    """Fetch PrivatePerson change batches from the local Apple Bridge."""

    def __init__(self, client: AppleBridgeClient) -> None:
        self._client = client

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        path = "/contacts/changes"
        if cursor is not None and cursor.value:
            path = f"{path}?{urlencode({'cursor': cursor.value})}"

        payload = await self._get_json(path)
        if payload.get("authorised") is False:
            return ChangeBatch(items=[], next_cursor=None, exhausted=True)

        items_raw = payload.get("items") or []
        if not isinstance(items_raw, list):
            raise AppleBridgeError("Apple Contacts changes payload missing items list")

        items: list[dict[str, Any]] = []
        for raw in items_raw:
            if not isinstance(raw, dict):
                raise AppleBridgeError("Apple Contacts item is not an object")
            person = _person_from_bridge(raw)
            items.append(person.model_dump(mode="json"))

        next_cursor = _cursor_from_payload(payload.get("next_cursor"))
        exhausted = bool(payload.get("exhausted", True))
        return ChangeBatch(items=items, next_cursor=next_cursor, exhausted=exhausted)

    async def _get_json(self, path: str) -> dict[str, Any]:
        """HTTP GET scoped to contacts — does not extend shared bridge_client (M07)."""
        if not self._client.token:
            raise AppleBridgeError("Apple Bridge token is not configured")

        headers = {"Authorization": f"Bearer {self._client.token}"}
        if self._client._transport is not None:
            async with httpx.AsyncClient(
                base_url=self._client.base_url,
                transport=self._client._transport,
                timeout=self._client.timeout,
            ) as client:
                try:
                    response = await client.get(path, headers=headers)
                except httpx.HTTPError as exc:
                    raise AppleBridgeError(f"Apple Bridge request failed: {exc}") from exc
        elif self._client.unix_socket:
            transport = httpx.AsyncHTTPTransport(uds=self._client.unix_socket)
            async with httpx.AsyncClient(
                base_url="http://localhost",
                transport=transport,
                timeout=self._client.timeout,
            ) as client:
                try:
                    response = await client.get(path, headers=headers)
                except httpx.HTTPError as exc:
                    raise AppleBridgeError(f"Apple Bridge request failed: {exc}") from exc
        else:
            async with httpx.AsyncClient(
                base_url=self._client.base_url,
                timeout=self._client.timeout,
            ) as client:
                try:
                    response = await client.get(path, headers=headers)
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


def _person_from_bridge(raw: dict[str, Any]) -> PrivatePerson:
    try:
        person_id = UUID(str(raw["id"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise AppleBridgeError("Apple Contacts item missing valid id UUID") from exc

    provider_ids = raw.get("provider_ids") or {}
    if not isinstance(provider_ids, dict):
        provider_ids = {}

    return PrivatePerson(
        id=person_id,
        display_name=_optional_str(raw.get("display_name")),
        aliases=_str_list(raw.get("aliases")),
        email_addresses=_str_list(raw.get("email_addresses")),
        phone_numbers=_str_list(raw.get("phone_numbers")),
        organisations=_str_list(raw.get("organisations")),
        provider_ids={str(k): str(v) for k, v in provider_ids.items()},
    )


def _cursor_from_payload(raw: Any) -> SyncCursor | None:
    if not isinstance(raw, dict):
        return None
    value = raw.get("value")
    if not isinstance(value, str) or not value:
        return None
    source = raw.get("source")
    return SyncCursor(value=value, source=source if isinstance(source, str) else "apple_contacts")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
