from personal_enigma.fixtures import sample_calendar_event


def test_sample_calendar_event() -> None:
    event = sample_calendar_event()
    assert event.provider == "apple_calendar"
    assert event.title == "Fixture meeting"
