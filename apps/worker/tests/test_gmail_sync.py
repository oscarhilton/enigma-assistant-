"""Worker Gmail sync stub tests (recorded transport, no live network)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx

from personal_enigma.ingestion.sources.gmail import GmailSource
from personal_enigma.worker.google.gmail import GmailSyncRequest, run_gmail_sync

FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "packages"
    / "ingestion"
    / "tests"
    / "fixtures"
    / "gmail"
)


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/users/me/profile"):
        return httpx.Response(200, json=_load("profile.json"))
    if path.endswith("/users/me/messages") and request.method == "GET":
        return httpx.Response(200, json=_load("messages_list.json"))
    if path.endswith("/users/me/messages/msg_alpha"):
        return httpx.Response(200, json=_load("message_alpha.json"))
    if path.endswith("/users/me/messages/msg_beta"):
        return httpx.Response(200, json=_load("message_beta.json"))
    return httpx.Response(404, json={"error": "not_found"})


def test_run_gmail_sync_with_remote_llm_disabled() -> None:
    async def _run() -> None:
        source = GmailSource(
            access_token="test-token",
            transport=httpx.MockTransport(_handler),
            remote_llm_enabled=False,
        )
        result = await run_gmail_sync(
            GmailSyncRequest(access_token="test-token", remote_llm_enabled=False),
            source=source,
        )
        assert result.message_count == 2
        assert result.next_cursor == "9001"
        assert result.remote_llm_enabled is False

    asyncio.run(_run())
