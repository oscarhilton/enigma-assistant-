"""Google Calendar DataSource adapter — owned by ticket M12.

Read-only Calendar API ingestion into ``PrivateCalendarEvent``. Never calls a
hosted model; remote LLM state does not affect ingest. Calendars are only read
when the user has explicitly selected them (no blind import).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time
from typing import Any, Literal, Protocol, runtime_checkable
from urllib.parse import quote

import httpx

from personal_enigma.domain import PrivateCalendarEvent, PrivatePersonRef, RecurrenceInfo
from personal_enigma.ingestion.protocol import ChangeBatch, SyncCursor

Availability = Literal["busy", "free", "tentative", "unavailable"]

GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
SOURCE_NAME = "google_calendar"
CALENDAR_READONLY_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


class GoogleCalendarError(RuntimeError):
    """Raised when the Google Calendar API cannot be reached or returns an error."""


@runtime_checkable
class PersonRefResolver(Protocol):
    """Soft dependency on Contacts-backed identity (M10)."""

    def resolve_ref(self, ref: PrivatePersonRef) -> object | None:
        """Return a pseudonym or contact handle when the ref is known."""
        ...


def _parse_google_datetime(payload: Mapping[str, Any] | None) -> tuple[datetime, bool]:
    """Return (instant, all_day) from a Google ``start`` / ``end`` object."""
    if not payload:
        raise GoogleCalendarError("Google Calendar event missing start/end")
    if "dateTime" in payload and payload["dateTime"]:
        raw = str(payload["dateTime"])
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed, False
    if "date" in payload and payload["date"]:
        day = date.fromisoformat(str(payload["date"]))
        return datetime.combine(day, time.min, tzinfo=UTC), True
    raise GoogleCalendarError("Google Calendar event start/end lacked dateTime/date")


def _availability(raw: Mapping[str, Any]) -> Availability | None:
    transparency = str(raw.get("transparency") or "opaque").lower()
    if transparency == "transparent":
        return "free"
    status = str(raw.get("status") or "").lower()
    if status == "tentative":
        return "tentative"
    if status == "cancelled":
        return None
    return "busy"


def _person_from_google(raw: Mapping[str, Any] | None) -> PrivatePersonRef | None:
    if not raw:
        return None
    email = raw.get("email")
    display = raw.get("displayName")
    email_str = str(email).strip() if email else None
    display_str = str(display).strip() if display else None
    if not email_str and not display_str:
        return None
    return PrivatePersonRef(
        display_name=display_str or None,
        email=email_str.lower() if email_str else None,
        provider_id=f"mailto:{email_str.lower()}" if email_str else None,
    )


def _recurrence(raw: Mapping[str, Any]) -> RecurrenceInfo | None:
    rules = raw.get("recurrence")
    if not isinstance(rules, list) or not rules:
        return None
    rrule = next((str(item) for item in rules if str(item).startswith("RRULE:")), None)
    rule = rrule.removeprefix("RRULE:") if rrule else str(rules[0])
    return RecurrenceInfo(rule=rule, raw={"recurrence": [str(item) for item in rules]})


def _cursor_payload(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): str(token) for key, token in parsed.items() if token}


def _encode_cursor(tokens: Mapping[str, str]) -> SyncCursor:
    return SyncCursor(value=json.dumps(dict(tokens), sort_keys=True), source=SOURCE_NAME)


class GoogleCalendarSource:
    """Read-only Google Calendar ``DataSource`` (events.list + syncToken)."""

    def __init__(
        self,
        *,
        access_token: str,
        selected_calendar_ids: Sequence[str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        base_url: str = GOOGLE_CALENDAR_API_BASE,
        timeout: float = 30.0,
        page_size: int = 100,
        contacts_by_email: Mapping[str, PrivatePersonRef] | None = None,
        entity_resolver: PersonRefResolver | None = None,
        remote_llm_enabled: bool = False,
    ) -> None:
        self.access_token = access_token
        self.selected_calendar_ids = [cid for cid in (selected_calendar_ids or []) if cid]
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
        self._calendar_meta: dict[str, dict[str, Any]] = {}

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            raise GoogleCalendarError("Google Calendar access token is not configured")
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
                raise GoogleCalendarError(f"Google Calendar request failed: {exc}") from exc

        if response.status_code == 401:
            raise GoogleCalendarError("Google Calendar rejected access token")
        if response.status_code == 410:
            raise GoogleCalendarError("Google Calendar sync token expired")
        if response.status_code >= 400:
            raise GoogleCalendarError(
                f"Google Calendar returned HTTP {response.status_code}: {response.text}"
            )
        return response.json()

    def _enrich_ref(self, ref: PrivatePersonRef | None) -> PrivatePersonRef | None:
        if ref is None:
            return None
        email_addr = (ref.email or "").lower()
        if email_addr and email_addr in self.contacts_by_email:
            known = self.contacts_by_email[email_addr]
            ref = PrivatePersonRef(
                display_name=known.display_name or ref.display_name,
                email=ref.email or known.email,
                provider_id=known.provider_id or ref.provider_id,
            )
        if self.entity_resolver is not None:
            self.entity_resolver.resolve_ref(ref)
        return ref

    def event_from_google(
        self,
        raw: Mapping[str, Any],
        *,
        calendar_id: str,
        calendar_name: str | None = None,
    ) -> PrivateCalendarEvent | None:
        """Map a Google Calendar event resource to ``PrivateCalendarEvent``."""
        if str(raw.get("status") or "").lower() == "cancelled":
            return None
        provider_event_id = str(raw.get("id") or "")
        if not provider_event_id:
            raise GoogleCalendarError("Google Calendar event missing id")

        start_at, all_day_start = _parse_google_datetime(
            raw.get("start") if isinstance(raw.get("start"), Mapping) else None
        )
        end_at, all_day_end = _parse_google_datetime(
            raw.get("end") if isinstance(raw.get("end"), Mapping) else None
        )
        all_day = all_day_start or all_day_end

        availability = _availability(raw)
        if availability is None:
            return None

        organiser = self._enrich_ref(
            _person_from_google(
                raw.get("organizer") if isinstance(raw.get("organizer"), Mapping) else None
            )
        )
        attendees: list[PrivatePersonRef] = []
        for item in raw.get("attendees") or []:
            if not isinstance(item, Mapping):
                continue
            person = self._enrich_ref(_person_from_google(item))
            if person is not None:
                attendees.append(person)

        updated_at = None
        if raw.get("updated"):
            updated_at = datetime.fromisoformat(str(raw["updated"]).replace("Z", "+00:00"))
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)

        title = str(raw.get("summary") or "").strip() or "(untitled)"
        return PrivateCalendarEvent(
            id=f"google_calendar:{calendar_id}:{provider_event_id}",
            provider="google_calendar",
            provider_event_id=provider_event_id,
            calendar_id=calendar_id,
            calendar_name=calendar_name,
            title=title,
            description=str(raw["description"]) if raw.get("description") is not None else None,
            location=str(raw["location"]) if raw.get("location") is not None else None,
            url=str(raw["htmlLink"]) if raw.get("htmlLink") is not None else None,
            start_at=start_at,
            end_at=end_at,
            all_day=all_day,
            availability=availability,
            organiser=organiser,
            attendees=attendees,
            recurrence=_recurrence(raw),
            updated_at=updated_at,
        )

    async def list_calendars(self) -> list[dict[str, str]]:
        """Return calendarList entries for selection UI (id + summary)."""
        payload = await self._get_json("/users/me/calendarList")
        if not isinstance(payload, dict):
            raise GoogleCalendarError("Google calendarList payload was not an object")
        calendars: list[dict[str, str]] = []
        for item in payload.get("items") or []:
            if not isinstance(item, Mapping) or not item.get("id"):
                continue
            calendar_id = str(item["id"])
            summary = str(item.get("summary") or calendar_id)
            self._calendar_meta[calendar_id] = dict(item)
            calendars.append({"id": calendar_id, "summary": summary})
        return calendars

    async def _ensure_calendar_meta(self, calendar_id: str) -> str | None:
        if calendar_id in self._calendar_meta:
            summary = self._calendar_meta[calendar_id].get("summary")
            return str(summary) if summary else None
        # Lightweight probe via calendarList; ignore failures and continue without name.
        try:
            await self.list_calendars()
        except GoogleCalendarError:
            return None
        summary = self._calendar_meta.get(calendar_id, {}).get("summary")
        return str(summary) if summary else None

    async def _list_events_page(
        self,
        calendar_id: str,
        *,
        sync_token: str | None,
        page_token: str | None,
    ) -> tuple[list[dict[str, Any]], str | None, str | None]:
        encoded = quote(calendar_id, safe="@.")
        params: dict[str, str] = {"maxResults": str(self.page_size)}
        if sync_token:
            params["syncToken"] = sync_token
        else:
            params["singleEvents"] = "false"
        if page_token:
            params["pageToken"] = page_token

        payload = await self._get_json(f"/calendars/{encoded}/events", params=params)
        if not isinstance(payload, dict):
            raise GoogleCalendarError("Google Calendar events payload was not an object")
        items = [
            dict(item)
            for item in (payload.get("items") or [])
            if isinstance(item, Mapping)
        ]
        next_page = payload.get("nextPageToken")
        next_sync = payload.get("nextSyncToken")
        return (
            items,
            str(next_page) if next_page else None,
            str(next_sync) if next_sync else None,
        )

    async def _events_for_calendar(
        self, calendar_id: str, *, sync_token: str | None
    ) -> tuple[list[PrivateCalendarEvent], str | None]:
        calendar_name = await self._ensure_calendar_meta(calendar_id)
        collected: list[dict[str, Any]] = []
        page_token: str | None = None
        active_sync = sync_token
        next_sync: str | None = sync_token

        while True:
            try:
                page, page_token, page_sync = await self._list_events_page(
                    calendar_id,
                    sync_token=active_sync,
                    page_token=page_token,
                )
            except GoogleCalendarError as exc:
                if active_sync and "sync token expired" in str(exc).lower():
                    # Full resync for this calendar.
                    active_sync = None
                    page_token = None
                    collected.clear()
                    continue
                raise

            collected.extend(page)
            if page_sync:
                next_sync = page_sync
            if not page_token:
                break

        events: list[PrivateCalendarEvent] = []
        for raw in collected:
            mapped = self.event_from_google(
                raw, calendar_id=calendar_id, calendar_name=calendar_name
            )
            if mapped is not None:
                events.append(mapped)
        return events, next_sync

    async def get_changes(self, cursor: SyncCursor | None) -> ChangeBatch:
        """Fetch events from user-selected calendars since ``cursor``.

        Empty ``selected_calendar_ids`` yields an empty batch (no blind import).
        """
        _ = self.remote_llm_enabled  # documented independence from remote inference

        if not self.selected_calendar_ids:
            return ChangeBatch(items=[], next_cursor=cursor, exhausted=True)

        prior_tokens = _cursor_payload(cursor.value if cursor else None)
        next_tokens: dict[str, str] = dict(prior_tokens)
        items: list[dict[str, Any]] = []

        for calendar_id in self.selected_calendar_ids:
            events, sync_token = await self._events_for_calendar(
                calendar_id, sync_token=prior_tokens.get(calendar_id)
            )
            for event in events:
                items.append(event.model_dump(mode="json"))
            if sync_token:
                next_tokens[calendar_id] = sync_token

        return ChangeBatch(
            items=items,
            next_cursor=_encode_cursor(next_tokens) if next_tokens else None,
            exhausted=True,
        )
