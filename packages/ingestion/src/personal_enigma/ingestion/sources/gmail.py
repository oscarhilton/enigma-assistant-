"""Gmail DataSource adapter — owned by ticket M11.

Read-only Gmail API ingestion into ``PrivateMessage``. Works with remote LLM
disabled: this module never calls a hosted model; it only fetches mail and maps
to the private domain.
"""

from __future__ import annotations

import base64
import email.utils
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Protocol, runtime_checkable

import httpx

from personal_enigma.domain import PrivateMessage, PrivatePersonRef
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
SOURCE_NAME = "gmail"

_ANGLE_EMAIL = re.compile(r"<([^>]+)>")
_BARE_EMAIL = re.compile(r"^[^<>\s@]+@[^<>\s@]+\.[^<>\s@]+$")


class GmailError(RuntimeError):
    """Raised when the Gmail API cannot be reached or returns an error."""


@runtime_checkable
class PersonRefResolver(Protocol):
    """Soft dependency on Contacts-backed identity (M10)."""

    def resolve_ref(self, ref: PrivatePersonRef) -> object | None:
        """Return a pseudonym or contact handle when the ref is known."""
        ...


def _decode_body_data(data: str | None) -> str | None:
    if not data:
        return None
    padded = data + "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    return raw.decode("utf-8", errors="replace")


def _header_map(payload: Mapping[str, Any]) -> dict[str, str]:
    headers = payload.get("headers") or []
    out: dict[str, str] = {}
    for item in headers:
        name = item.get("name")
        value = item.get("value")
        if isinstance(name, str) and isinstance(value, str):
            out[name.lower()] = value
    return out


def _parse_address(raw: str) -> PrivatePersonRef:
    display_name, addr = email.utils.parseaddr(raw)
    email_addr = addr.strip() or None
    name = display_name.strip() or None
    if email_addr is None:
        stripped = raw.strip()
        if _BARE_EMAIL.match(stripped):
            email_addr = stripped
        else:
            angle = _ANGLE_EMAIL.search(raw)
            if angle:
                email_addr = angle.group(1)
    return PrivatePersonRef(display_name=name, email=email_addr)


def _parse_address_list(raw: str | None) -> list[PrivatePersonRef]:
    if not raw:
        return []
    refs: list[PrivatePersonRef] = []
    for name, addr in email.utils.getaddresses([raw]):
        email_addr = addr.strip() or None
        display = name.strip() or None
        if not email_addr and not display:
            continue
        refs.append(PrivatePersonRef(display_name=display, email=email_addr))
    return refs


def _extract_plain_text(payload: Mapping[str, Any] | None) -> str | None:
    if not payload:
        return None
    mime = payload.get("mimeType")
    body = payload.get("body") or {}
    if mime == "text/plain":
        return _decode_body_data(body.get("data") if isinstance(body, dict) else None)
    parts = payload.get("parts") or []
    if isinstance(parts, list):
        for part in parts:
            if isinstance(part, dict):
                text = _extract_plain_text(part)
                if text:
                    return text
    if mime == "text/html":
        # Last resort: return decoded HTML when no plain part exists.
        return _decode_body_data(body.get("data") if isinstance(body, dict) else None)
    return None


def _ms_to_datetime(value: str | int | None) -> datetime | None:
    if value is None:
        return None
    try:
        millis = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(millis / 1000, tz=UTC)


def _parse_date_header(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


class GmailSource:
    """Read-only Gmail ``DataSource`` using the users.messages / history APIs."""

    def __init__(
        self,
        *,
        access_token: str,
        transport: httpx.AsyncBaseTransport | None = None,
        base_url: str = GMAIL_API_BASE,
        timeout: float = 30.0,
        page_size: int = 50,
        contacts_by_email: Mapping[str, PrivatePersonRef] | None = None,
        entity_resolver: PersonRefResolver | None = None,
        remote_llm_enabled: bool = False,
    ) -> None:
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.page_size = page_size
        self.contacts_by_email = {
            key.lower(): value for key, value in (contacts_by_email or {}).items()
        }
        self.entity_resolver = entity_resolver
        # Ingest must succeed regardless of remote inference; default is off.
        self.remote_llm_enabled = remote_llm_enabled
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            raise GmailError("Gmail access token is not configured")
        return {"Authorization": f"Bearer {self.access_token}"}

    def _client(self) -> httpx.AsyncClient:
        if self._transport is not None:
            return httpx.AsyncClient(
                base_url=self.base_url,
                transport=self._transport,
                timeout=self.timeout,
            )
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def _get_json(self, path: str, *, params: Mapping[str, str] | None = None) -> Any:
        async with self._client() as client:
            try:
                response = await client.get(path, headers=self._headers(), params=params)
            except httpx.HTTPError as exc:
                raise GmailError(f"Gmail request failed: {exc}") from exc

        if response.status_code == 401:
            raise GmailError("Gmail rejected access token")
        if response.status_code >= 400:
            raise GmailError(f"Gmail returned HTTP {response.status_code}: {response.text}")
        return response.json()

    def _enrich_ref(self, ref: PrivatePersonRef) -> PrivatePersonRef:
        email_addr = (ref.email or "").lower()
        if email_addr and email_addr in self.contacts_by_email:
            known = self.contacts_by_email[email_addr]
            ref = PrivatePersonRef(
                display_name=known.display_name or ref.display_name,
                email=ref.email or known.email,
                provider_id=known.provider_id or ref.provider_id,
            )
        if self.entity_resolver is not None:
            # Soft M10 hook: exercise Contacts-backed resolution when available.
            self.entity_resolver.resolve_ref(ref)
        return ref

    def message_from_gmail(self, raw: Mapping[str, Any]) -> PrivateMessage:
        """Map a Gmail ``users.messages`` resource to ``PrivateMessage``."""
        provider_message_id = str(raw["id"])
        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
        headers = _header_map(payload) if isinstance(payload, dict) else {}

        from_person = None
        if headers.get("from"):
            from_person = self._enrich_ref(_parse_address(headers["from"]))
        to = [self._enrich_ref(r) for r in _parse_address_list(headers.get("to"))]
        cc = [self._enrich_ref(r) for r in _parse_address_list(headers.get("cc"))]

        received_at = _ms_to_datetime(raw.get("internalDate"))
        sent_at = _parse_date_header(headers.get("date")) or received_at
        labels = [str(label) for label in (raw.get("labelIds") or [])]

        body_text = _extract_plain_text(payload if isinstance(payload, dict) else None)

        return PrivateMessage(
            id=f"gmail:{provider_message_id}",
            provider="gmail",
            provider_message_id=provider_message_id,
            thread_id=str(raw["threadId"]) if raw.get("threadId") else None,
            subject=headers.get("subject"),
            snippet=str(raw["snippet"]) if raw.get("snippet") is not None else None,
            body_text=body_text,
            from_person=from_person,
            to=to,
            cc=cc,
            sent_at=sent_at,
            received_at=received_at,
            labels=labels,
        )

    async def _fetch_message(self, message_id: str) -> PrivateMessage:
        raw = await self._get_json(
            f"/users/me/messages/{message_id}",
            params={"format": "full"},
        )
        if not isinstance(raw, dict):
            raise GmailError("Gmail message payload was not an object")
        return self.message_from_gmail(raw)

    async def _list_message_ids(
        self, *, page_token: str | None = None
    ) -> tuple[list[str], str | None]:
        params: dict[str, str] = {"maxResults": str(self.page_size)}
        if page_token:
            params["pageToken"] = page_token
        payload = await self._get_json("/users/me/messages", params=params)
        if not isinstance(payload, dict):
            raise GmailError("Gmail list payload was not an object")
        ids = [
            str(item["id"])
            for item in (payload.get("messages") or [])
            if isinstance(item, dict) and item.get("id")
        ]
        next_page = payload.get("nextPageToken")
        return ids, str(next_page) if next_page else None

    async def _history_message_ids(self, start_history_id: str) -> tuple[list[str], str]:
        ids: list[str] = []
        history_id = start_history_id
        page_token: str | None = None
        while True:
            params: dict[str, str] = {
                "startHistoryId": start_history_id,
                "historyTypes": "messageAdded",
                "maxResults": str(self.page_size),
            }
            if page_token:
                params["pageToken"] = page_token
            payload = await self._get_json("/users/me/history", params=params)
            if not isinstance(payload, dict):
                raise GmailError("Gmail history payload was not an object")
            for entry in payload.get("history") or []:
                if not isinstance(entry, dict):
                    continue
                for added in entry.get("messagesAdded") or []:
                    if not isinstance(added, dict):
                        continue
                    message = added.get("message") or {}
                    if isinstance(message, dict) and message.get("id"):
                        ids.append(str(message["id"]))
            history_id = str(payload.get("historyId") or history_id)
            next_page = payload.get("nextPageToken")
            if not next_page:
                break
            page_token = str(next_page)
        return ids, history_id

    async def _profile_history_id(self) -> str:
        profile = await self._get_json("/users/me/profile")
        if not isinstance(profile, dict) or not profile.get("historyId"):
            raise GmailError("Gmail profile did not include historyId")
        return str(profile["historyId"])

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        """Fetch new/changed messages since ``cursor`` (Gmail historyId).

        Remote LLM state is ignored: ingestion is always local-only.
        """
        _ = self.remote_llm_enabled  # documented independence from remote inference

        if cursor is None or not cursor.value:
            message_ids: list[str] = []
            page_token: str | None = None
            while True:
                page_ids, page_token = await self._list_message_ids(page_token=page_token)
                message_ids.extend(page_ids)
                if not page_token:
                    break
            history_id = await self._profile_history_id()
        else:
            message_ids, history_id = await self._history_message_ids(cursor.value)

        # Preserve order while dropping duplicates from history fan-out.
        seen: set[str] = set()
        unique_ids: list[str] = []
        for message_id in message_ids:
            if message_id not in seen:
                seen.add(message_id)
                unique_ids.append(message_id)

        items: list[dict[str, Any]] = []
        for message_id in unique_ids:
            message = await self._fetch_message(message_id)
            items.append(message.model_dump(mode="json"))

        return ChangeBatch(
            items=items,
            next_cursor=SyncCursor(value=history_id, source=SOURCE_NAME),
            exhausted=True,
        )
