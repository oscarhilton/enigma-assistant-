"""Default remote privacy levels for source types."""

from enum import StrEnum

from personal_enigma.domain import SourceType


class PrivacyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


_DEFAULTS: dict[SourceType, PrivacyLevel] = {
    SourceType.EMAIL: PrivacyLevel.MEDIUM,
    SourceType.CALENDAR_EVENT: PrivacyLevel.MEDIUM,
    SourceType.REMINDER: PrivacyLevel.MEDIUM,
    SourceType.CONTACT: PrivacyLevel.HIGH,
    SourceType.NOTE: PrivacyLevel.HIGH,
}


def default_level_for_source(source: SourceType) -> PrivacyLevel:
    """Return the default remote privacy level for a source type."""
    return _DEFAULTS[source]
