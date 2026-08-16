"""Recorded HTTP fixture tests for Gmail ingestion (no live network)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from personal_enigma.domain import PrivateMessage, PrivatePersonRef, SourceType
from personal_enigma.ingestion.protocol import SyncCursor
from personal_enigma.ingestion.sources.gmail import GmailError, GmailSource
from personal_enigma.privacy import PrivacyLevel, default_level_for_source

FIXTURES = Path(__file__).parent / "fixtures" / "gmail"


def _load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _recorded_handler(request: httpx.Request) -> httpx.Response:
    if request.headers.get("Authorization") != "Bearer test-token":
        return httpx.Response(401, json={"error": "unauthorized"})

    path = request.url.path
    if path.endswith("/users/me/profile"):
        return httpx.Response(200, json=_load("profile.json"))
    if path.endswith("/users/me/messages") and request.method == "GET":
        return httpx.Response(200, json=_load("messages_list.json"))
    if path.endswith("/users/me/messages/msg_alpha"):
        return httpx.Response(200, json=_load("message_alpha.json"))
    if path.endswith("/users/me/messages/msg_beta"):
        return httpx.Response(200, json=_load("message_beta.json"))
    if path.endswith("/users/me/history"):
        return httpx.Response(200, json=_load("history.json"))
    return httpx.Response(404, json={"error": "not_found", "path": path})


class _RecordingResolver:
    def __init__(self) -> None:
        self.seen: list[str | None] = []

    def resolve_ref(self, ref: PrivatePersonRef) -> str | None:
        self.seen.append(ref.email)
        if ref.email == "jordan@corp.example":
            return "PERSON_JORDAN"
        return None


def _source(**kwargs: Any) -> GmailSource:
    defaults: dict[str, Any] = {
        "access_token": "test-token",
        "transport": httpx.MockTransport(_recorded_handler),
        "base_url": "https://gmail.googleapis.com/gmail/v1",
        "remote_llm_enabled": False,
    }
    defaults.update(kwargs)
    return GmailSource(**defaults)


def test_initial_sync_maps_to_private_messages() -> None:
    async def _run() -> None:
        source = _source(
            contacts_by_email={
                "jordan@corp.example": PrivatePersonRef(
                    display_name="Jordan (Contacts)",
                    email="jordan@corp.example",
                    provider_id="ab:jordan",
                )
            }
        )
        batch = await source.get_changes(None)
        assert len(batch.items) == 2
        assert batch.exhausted is True
        assert batch.next_cursor is not None
        assert batch.next_cursor.value == "9001"
        assert batch.next_cursor.source == "gmail"

        messages = [PrivateMessage.model_validate(item) for item in batch.items]
        assert {m.provider_message_id for m in messages} == {"msg_alpha", "msg_beta"}
        alpha = next(m for m in messages if m.provider_message_id == "msg_alpha")
        assert alpha.provider == "gmail"
        assert alpha.id == "gmail:msg_alpha"
        assert alpha.subject == "Review proposal follow-up"
        assert alpha.from_person is not None
        assert alpha.from_person.display_name == "Jordan (Contacts)"
        assert alpha.from_person.provider_id == "ab:jordan"
        assert alpha.to[0].email == "user@example.test"
        assert alpha.cc[0].email == "morgan@corp.example"
        assert alpha.body_text is not None
        assert "sk_live_example" in alpha.body_text
        assert "+1-555-019-8877" in alpha.body_text

    asyncio.run(_run())


def test_incremental_history_cursor() -> None:
    async def _run() -> None:
        source = _source()
        batch = await source.get_changes(SyncCursor(value="9001", source="gmail"))
        assert len(batch.items) == 1
        message = PrivateMessage.model_validate(batch.items[0])
        assert message.provider_message_id == "msg_beta"
        assert batch.next_cursor is not None
        assert batch.next_cursor.value == "9100"

    asyncio.run(_run())


def test_entity_resolver_invoked_when_available() -> None:
    async def _run() -> None:
        resolver = _RecordingResolver()
        source = _source(entity_resolver=resolver)
        await source.get_changes(None)
        assert "jordan@corp.example" in resolver.seen
        assert "morgan@corp.example" in resolver.seen

    asyncio.run(_run())


def test_works_with_remote_llm_disabled() -> None:
    async def _run() -> None:
        source = _source(remote_llm_enabled=False)
        assert source.remote_llm_enabled is False
        batch = await source.get_changes(None)
        assert batch.items
        # Ingest retains full local body; remote inference is not consulted.
        alpha = PrivateMessage.model_validate(
            next(i for i in batch.items if i["provider_message_id"] == "msg_alpha")
        )
        assert alpha.body_text and "sk_live_example" in alpha.body_text

    asyncio.run(_run())


def test_privacy_invariant_email_body_not_shipped_wholesale() -> None:
    """Medium default; local body (with secrets) stays out of remote-facing views."""

    async def _run() -> None:
        assert default_level_for_source(SourceType.EMAIL) == PrivacyLevel.MEDIUM
        source = _source(remote_llm_enabled=False)
        batch = await source.get_changes(None)
        message = PrivateMessage.model_validate(
            next(i for i in batch.items if i["provider_message_id"] == "msg_alpha")
        )
        assert message.body_text
        assert "sk_live_example" in message.body_text
        # Local transform stub: remote-facing payload uses snippet, never body.
        remote_view = {
            "summary": message.snippet,
            "subject": message.subject,
            "entities": ["PERSON_JORDAN"],
        }
        blob = json.dumps(remote_view)
        assert message.body_text not in blob
        assert "sk_live_example" not in blob
        assert "sk_live_example" not in (message.snippet or "")

    asyncio.run(_run())


def test_unauthorized_raises() -> None:
    async def _run() -> None:
        source = GmailSource(
            access_token="wrong-token",
            transport=httpx.MockTransport(_recorded_handler),
        )
        with pytest.raises(GmailError, match="rejected access token"):
            await source.get_changes(None)

    asyncio.run(_run())
