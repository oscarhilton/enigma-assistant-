from personal_enigma.domain.enums import Provider, SourceType


def test_source_type_values() -> None:
    assert SourceType.CALENDAR_EVENT == "calendar_event"
    assert SourceType.REMINDER == "reminder"
    assert SourceType.NOTE == "note"
    assert SourceType.CONTACT == "contact"
    assert SourceType.EMAIL == "email"


def test_provider_values() -> None:
    assert Provider.APPLE == "apple"
    assert Provider.GOOGLE == "google"
    assert Provider.LOCAL == "local"
