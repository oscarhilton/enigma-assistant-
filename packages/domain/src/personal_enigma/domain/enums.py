"""Source, provider, and NextAction enums.

SourceType describes *what* something is.
Provider describes *where* it came from.
ActionCategory / Effort / Urgency / ActionContext describe optional NextAction.
"""

from enum import StrEnum


class SourceType(StrEnum):
    EMAIL = "email"
    CALENDAR_EVENT = "calendar_event"
    REMINDER = "reminder"
    NOTE = "note"
    CONTACT = "contact"
    CHAT_MESSAGE = "chat_message"


class Provider(StrEnum):
    GOOGLE = "google"
    APPLE = "apple"
    LOCAL = "local"
    WHATSAPP = "whatsapp"


class ActionCategory(StrEnum):
    """Kind of optional next use of attention — not an Attention interrupt class."""

    OBLIGATION = "obligation"
    OPEN_LOOP = "open_loop"
    MAINTENANCE = "maintenance"
    ADMIN = "admin"
    COMMUNICATION = "communication"
    PREPARATION = "preparation"
    CREATIVE = "creative"
    LEARNING = "learning"
    MOVEMENT = "movement"
    REST = "rest"
    SOCIAL = "social"
    HOUSEHOLD = "household"
    NOTHING = "nothing"


class Effort(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Urgency(StrEnum):
    """Urgency on a NextAction — absent/none means urgency must not drive ranking."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionContext(StrEnum):
    """Situational tags that affect contextual fit (extensible)."""

    AT_DESK = "at_desk"
    AWAY_FROM_DESK = "away_from_desk"
    SHORT_WINDOW = "short_window"
    LONG_WINDOW = "long_window"
    HIGH_LOAD = "high_load"
    LOW_LOAD = "low_load"
    BEFORE_MEETING = "before_meeting"
    EVENING = "evening"
    WEEKEND = "weekend"
