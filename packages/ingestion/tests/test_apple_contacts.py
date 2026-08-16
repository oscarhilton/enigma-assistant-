from __future__ import annotations

import asyncio
from uuid import UUID

import httpx

from personal_enigma.ingestion.bridge_client import AppleBridgeClient
from personal_enigma.ingestion.protocol import SyncCursor
from personal_enigma.ingestion.sources.apple_contacts import AppleContactsSource

PERSON_ID = "a1b2c3d4-e5f6-4789-8abc-def012345678"
CONTACT_PAYLOAD = {
    "items": [
        {
            "id": PERSON_ID,
            "display_name": "Joseph Atkinson",
            "aliases": ["Joe"],
            "email_addresses": ["joe@example.com"],
            "phone_numbers": [],
            "organisations": [],
            "provider_ids": {"apple_contacts": "AB-joseph"},
        }
    ],
    "next_cursor": {"value": "cursor-1", "source": "apple_contacts"},
    "exhausted": True,
    "authorised": True,
}


def _handler(request: httpx.Request) -> httpx.Response:
    if request.headers.get("Authorization") != "Bearer test-token":
        return httpx.Response(401, json={"error": "unauthorized"})
    if request.url.path == "/contacts/changes":
        if request.url.params.get("cursor") == "cursor-1":
            return httpx.Response(
                200,
                json={
                    "items": [],
                    "next_cursor": {"value": "cursor-1", "source": "apple_contacts"},
                    "exhausted": True,
                    "authorised": True,
                },
            )
        return httpx.Response(200, json=CONTACT_PAYLOAD)
    return httpx.Response(404, json={"error": "not_found"})


def test_apple_contacts_maps_bridge_payload_to_change_batch() -> None:
    async def _run() -> None:
        client = AppleBridgeClient(
            token="test-token",
            transport=httpx.MockTransport(_handler),
        )
        source = AppleContactsSource(client)
        batch = await source.get_changes(None)
        assert len(batch.items) == 1
        person = batch.items[0]
        assert person["display_name"] == "Joseph Atkinson"
        assert person["email_addresses"] == ["joe@example.com"]
        assert person["provider_ids"]["apple_contacts"] == "AB-joseph"
        assert UUID(person["id"]) == UUID(PERSON_ID)
        assert batch.next_cursor is not None
        assert batch.next_cursor.value == "cursor-1"
        assert batch.exhausted is True

        again = await source.get_changes(SyncCursor(value="cursor-1", source="apple_contacts"))
        assert again.items == []
        assert again.exhausted is True

    asyncio.run(_run())


def test_apple_contacts_unauthorised_returns_empty_batch() -> None:
    def denied(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/contacts/changes":
            return httpx.Response(
                200,
                json={"items": [], "next_cursor": None, "exhausted": True, "authorised": False},
            )
        return httpx.Response(404)

    async def _run() -> None:
        client = AppleBridgeClient(token="test-token", transport=httpx.MockTransport(denied))
        source = AppleContactsSource(client)
        batch = await source.get_changes(None)
        assert batch.items == []
        assert batch.exhausted is True
        assert batch.next_cursor is None

    asyncio.run(_run())
