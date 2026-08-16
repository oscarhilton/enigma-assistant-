from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from personal_enigma.ingestion.bridge_client import AppleBridgeClient, AppleBridgeError

CAPABILITIES = {
    "calendar": {"available": True, "authorised": False},
    "reminders": {"available": True, "authorised": False},
    "contacts": {"available": True, "authorised": False},
    "notes": {"available": True, "authorised": False, "quality": "best_effort"},
}


def _handler(request: httpx.Request) -> httpx.Response:
    if request.headers.get("Authorization") != "Bearer test-token":
        return httpx.Response(401, json={"error": "unauthorized"})
    if request.url.path == "/health":
        return httpx.Response(200, json={"status": "ok", "service": "enigma-apple-bridge"})
    if request.url.path == "/capabilities":
        return httpx.Response(200, json=CAPABILITIES)
    return httpx.Response(404, json={"error": "not_found"})


def test_get_capabilities_with_bearer_token() -> None:
    async def _run() -> None:
        transport = httpx.MockTransport(_handler)
        client = AppleBridgeClient(token="test-token", transport=transport)
        payload = await client.get_capabilities()
        assert payload["notes"]["quality"] == "best_effort"
        assert payload["calendar"]["authorised"] is False

    asyncio.run(_run())


def test_get_health() -> None:
    async def _run() -> None:
        transport = httpx.MockTransport(_handler)
        client = AppleBridgeClient(token="test-token", transport=transport)
        payload = await client.get_health()
        assert payload["service"] == "enigma-apple-bridge"

    asyncio.run(_run())


def test_missing_token_raises() -> None:
    async def _run() -> None:
        client = AppleBridgeClient(token=None, transport=httpx.MockTransport(_handler))
        with pytest.raises(AppleBridgeError, match="token is not configured"):
            await client.get_capabilities()

    asyncio.run(_run())


def test_unauthorized_raises() -> None:
    async def _run() -> None:
        transport = httpx.MockTransport(_handler)
        client = AppleBridgeClient(token="wrong-token", transport=transport)
        with pytest.raises(AppleBridgeError, match="rejected bearer token"):
            await client.get_capabilities()

    asyncio.run(_run())


def test_live_loopback_server_if_available() -> None:
    """Optional integration: hit a running bridge when ENIGMA_BRIDGE_TOKEN is set.

    macOS CI / local: start ``enigma-apple-bridge`` with the same token first.
    """
    import os

    token = os.environ.get("ENIGMA_BRIDGE_TOKEN")
    if not token:
        pytest.skip("ENIGMA_BRIDGE_TOKEN not set; skipping live bridge integration")

    async def _run() -> None:
        client = AppleBridgeClient(token=token)
        try:
            payload = await client.get_capabilities()
        except AppleBridgeError as exc:
            pytest.skip(f"bridge not reachable: {exc}")

        assert "calendar" in payload
        assert json.dumps(payload)

    asyncio.run(_run())


def test_capabilities_shape_matches_scaffold() -> None:
    assert set(CAPABILITIES) == {"calendar", "reminders", "contacts", "notes"}
