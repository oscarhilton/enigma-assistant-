"""Source and provider enums.

SourceType describes *what* something is.
Provider describes *where* it came from.
"""

from enum import StrEnum


class SourceType(StrEnum):
    EMAIL = "email"
    CALENDAR_EVENT = "calendar_event"
    REMINDER = "reminder"
    NOTE = "note"
    CONTACT = "contact"


class Provider(StrEnum):
    GOOGLE = "google"
    APPLE = "apple"
    LOCAL = "local"
