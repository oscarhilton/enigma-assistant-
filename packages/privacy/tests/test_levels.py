from personal_enigma.domain import SourceType
from personal_enigma.privacy import PrivacyLevel, default_level_for_source


def test_notes_default_high() -> None:
    assert default_level_for_source(SourceType.NOTE) == PrivacyLevel.HIGH


def test_contacts_default_high() -> None:
    assert default_level_for_source(SourceType.CONTACT) == PrivacyLevel.HIGH


def test_calendar_default_medium() -> None:
    assert default_level_for_source(SourceType.CALENDAR_EVENT) == PrivacyLevel.MEDIUM


def test_chat_message_default_very_high() -> None:
    assert default_level_for_source(SourceType.CHAT_MESSAGE) == PrivacyLevel.VERY_HIGH
