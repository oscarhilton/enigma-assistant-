"""Gmail fixture transport — nasty synthetic mailbox through real parser path (SEC-04).

Feeds recorded Gmail API JSON (and manifest-derived adversarial/canary messages)
through the same ``GmailSource`` code path used for live ``gmail.readonly`` sync.
No live Google credentials required for CI.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx

from personal_enigma.fixtures.adversarial_email_cases import AdversarialEmailCase
from personal_enigma.fixtures.alex_sensitive_canaries import SensitiveCanary
from personal_enigma.fixtures.nasty_mailbox_manifest import (
    GMAIL_NASTY_FIXTURE_ROOT,
    NASTY_MAILBOX_MATRIX,
    FixtureKind,
)

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
_REPO_ROOT = Path(__file__).resolve().parents[5]


def _b64url(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def _basic_headers(
    *,
    subject: str,
    from_addr: str = "Hostile Sender <hostile@example.test>",
) -> list[dict[str, str]]:
    return [
        {"name": "From", "value": from_addr},
        {"name": "To", "value": "User <user@example.test>"},
        {"name": "Subject", "value": subject},
        {"name": "Date", "value": "Fri, 16 Aug 2024 12:00:00 +0000"},
    ]


def adversarial_case_to_gmail_json(
    case: AdversarialEmailCase,
    *,
    message_id: str | None = None,
) -> dict[str, Any]:
    """Build a Gmail ``users.messages`` resource from an SEC-03 adversarial case."""
    msg_id = message_id or f"adv-{case.case_id}"
    snippet = (case.body_plain[:120] + "…") if len(case.body_plain) > 120 else case.body_plain

    if case.body_html:
        payload: dict[str, Any] = {
            "mimeType": "multipart/alternative",
            "headers": _basic_headers(subject=case.subject),
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": _b64url(case.body_plain)},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": _b64url(case.body_html)},
                },
            ],
        }
    else:
        payload = {
            "mimeType": "text/plain",
            "headers": _basic_headers(subject=case.subject),
            "body": {"data": _b64url(case.body_plain)},
        }

    return {
        "id": msg_id,
        "threadId": f"thread-{msg_id}",
        "labelIds": ["INBOX"],
        "snippet": snippet.replace("\n", " "),
        "internalDate": "1723814400000",
        "payload": payload,
    }


def canary_to_gmail_json(
    canary: SensitiveCanary,
    *,
    message_id: str | None = None,
) -> dict[str, Any]:
    """Build a Gmail message resource embedding synthetic canary secrets."""
    msg_id = message_id or f"canary-{canary.id}"
    body = canary.body_text
    snippet = (body[:120] + "…") if len(body) > 120 else body
    return {
        "id": msg_id,
        "threadId": f"thread-{msg_id}",
        "labelIds": ["INBOX"],
        "snippet": snippet.replace("\n", " "),
        "internalDate": "1723814400000",
        "payload": {
            "mimeType": "text/plain",
            "headers": _basic_headers(subject=canary.title),
            "body": {"data": _b64url(body)},
        },
    }


def load_gmail_api_fixture(relative_path: str) -> dict[str, Any]:
    """Load a Gmail API JSON fixture from the repo (manifest ``gmail_fixture`` path)."""
    path = _REPO_ROOT / relative_path
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Gmail fixture must be an object: {path}")
    return data


def build_nasty_mailbox_messages() -> dict[str, dict[str, Any]]:
    """Resolve every nasty mailbox manifest row to a Gmail API message dict."""
    from personal_enigma.fixtures.adversarial_email_cases import CASE_BY_ID
    from personal_enigma.fixtures.alex_sensitive_canaries import CANARY_BY_ID

    messages: dict[str, dict[str, Any]] = {}
    for entry in NASTY_MAILBOX_MATRIX:
        if entry.fixture_kind == FixtureKind.ADVERSARIAL_EMAIL:
            case = CASE_BY_ID[entry.adversarial_case_id or entry.fixture_id]
            msg = adversarial_case_to_gmail_json(case)
        elif entry.fixture_kind == FixtureKind.SENSITIVE_CANARY:
            canary = CANARY_BY_ID[entry.canary_id or entry.fixture_id]
            msg = canary_to_gmail_json(canary)
        elif entry.fixture_kind == FixtureKind.GMAIL_API_JSON:
            assert entry.gmail_fixture is not None
            msg = load_gmail_api_fixture(entry.gmail_fixture)
        else:
            continue
        messages[str(msg["id"])] = msg
    return messages


class GmailFixtureTransport(httpx.AsyncBaseTransport):
    """Mock Gmail API transport routing to nasty-mailbox fixture messages."""

    def __init__(
        self,
        messages: Mapping[str, Mapping[str, Any]] | None = None,
        *,
        history_id: str = "nasty-history-9001",
    ) -> None:
        self._messages = dict(messages) if messages is not None else build_nasty_mailbox_messages()
        self._history_id = history_id
        self._ids = list(self._messages.keys())

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.headers.get("Authorization") != "Bearer fixture-token":
            return httpx.Response(401, json={"error": "unauthorized"})

        path = request.url.path
        if path.endswith("/users/me/profile"):
            return httpx.Response(
                200,
                json={
                    "historyId": self._history_id,
                    "emailAddress": "test@example.test",
                },
            )
        if path.endswith("/users/me/messages") and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "messages": [
                        {"id": mid, "threadId": msg.get("threadId", mid)}
                        for mid, msg in self._messages.items()
                    ],
                    "resultSizeEstimate": len(self._messages),
                },
            )
        if "/users/me/messages/" in path:
            msg_id = path.rsplit("/", 1)[-1]
            if msg_id in self._messages:
                return httpx.Response(200, json=self._messages[msg_id])
            return httpx.Response(404, json={"error": "not_found", "id": msg_id})
        if path.endswith("/users/me/history"):
            return httpx.Response(
                200,
                json={
                    "history": [
                        {
                            "id": "1",
                            "messagesAdded": [{"message": {"id": mid}} for mid in self._ids],
                        }
                    ],
                    "historyId": self._history_id,
                },
            )
        return httpx.Response(404, json={"error": "not_found", "path": path})


__all__ = [
    "GMAIL_NASTY_FIXTURE_ROOT",
    "GmailFixtureTransport",
    "adversarial_case_to_gmail_json",
    "build_nasty_mailbox_messages",
    "canary_to_gmail_json",
    "load_gmail_api_fixture",
]
