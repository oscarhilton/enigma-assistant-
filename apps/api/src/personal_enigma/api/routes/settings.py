"""Settings API — calendar selection and Apple permission placeholders.

Persistence is in-memory until M00a lands a private DB. Payloads never include
note bodies or full contact records.
"""

from __future__ import annotations

from copy import deepcopy
from threading import Lock

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel, Field

router = APIRouter(tags=["settings"])


class CalendarSource(BaseModel):
    """A calendar Enigma may watch."""

    id: str
    name: str
    provider: str
    enabled: bool = True


class ApplePermissionPlaceholder(BaseModel):
    """Permission status stub until the Apple Bridge reports live capabilities."""

    id: str
    label: str
    status: str = "pending"
    detail: str = "pending Apple Bridge"


class SettingsResponse(BaseModel):
    calendars: list[CalendarSource]
    apple_permissions: list[ApplePermissionPlaceholder]
    scheduled_for_sync: list[str]


class CalendarSelectionUpdate(BaseModel):
    """Which calendar sources Enigma should watch."""

    enabled_ids: list[str] = Field(default_factory=list)


def _default_calendars() -> list[CalendarSource]:
    return [
        CalendarSource(
            id="apple:work",
            name="Work",
            provider="apple_calendar",
            enabled=True,
        ),
        CalendarSource(
            id="apple:personal",
            name="Personal",
            provider="apple_calendar",
            enabled=True,
        ),
        CalendarSource(
            id="google:team",
            name="Team",
            provider="google_calendar",
            enabled=False,
        ),
    ]


def _default_permissions() -> list[ApplePermissionPlaceholder]:
    return [
        ApplePermissionPlaceholder(
            id="calendar",
            label="Calendar",
            detail="read access (pending Apple Bridge)",
        ),
        ApplePermissionPlaceholder(
            id="reminders",
            label="Reminders",
            detail="read access (pending Apple Bridge)",
        ),
        ApplePermissionPlaceholder(
            id="contacts",
            label="Contacts",
            detail="read access (pending Apple Bridge)",
        ),
        ApplePermissionPlaceholder(
            id="notes",
            label="Notes",
            detail="automation, opt-in (pending Apple Bridge)",
        ),
    ]


class SettingsStore:
    """In-memory settings store (swap for sqlite/M00a later).

    Process-local only: use a single API worker until M00a private DB persistence.
    A lock serialises concurrent threadpool access within one process.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.calendars = _default_calendars()
            self.apple_permissions = _default_permissions()

    def scheduled_for_sync(self) -> list[str]:
        """Calendar ids that are enabled and therefore eligible for sync jobs."""
        with self._lock:
            return [cal.id for cal in self.calendars if cal.enabled]

    def snapshot(self) -> SettingsResponse:
        with self._lock:
            return SettingsResponse(
                calendars=deepcopy(self.calendars),
                apple_permissions=deepcopy(self.apple_permissions),
                scheduled_for_sync=[cal.id for cal in self.calendars if cal.enabled],
            )

    def set_enabled_calendars(self, enabled_ids: list[str]) -> SettingsResponse:
        enabled = set(enabled_ids)
        with self._lock:
            for cal in self.calendars:
                cal.enabled = cal.id in enabled
            return SettingsResponse(
                calendars=deepcopy(self.calendars),
                apple_permissions=deepcopy(self.apple_permissions),
                scheduled_for_sync=[cal.id for cal in self.calendars if cal.enabled],
            )


_store = SettingsStore()


def get_store() -> SettingsStore:
    return _store


def reset_settings_store() -> None:
    """Test helper — restore fixture defaults."""
    _store.reset()


def calendars_scheduled_for_sync() -> list[str]:
    """Public helper for workers: only enabled calendars are scheduled."""
    return _store.scheduled_for_sync()


@router.get("/api/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    return _store.snapshot()


@router.put("/api/settings/calendars", response_model=SettingsResponse)
def update_calendar_selection(body: CalendarSelectionUpdate) -> SettingsResponse:
    return _store.set_enabled_calendars(body.enabled_ids)


def install_settings_routes(app: FastAPI) -> None:
    """Attach settings routes to an application instance."""
    app.include_router(router)
