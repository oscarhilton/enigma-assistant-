from datetime import UTC, datetime

from personal_enigma.dedupe import calendar_evidence_from_event, dedupe_calendar_events
from personal_enigma.domain import CalendarEvidence, PrivateCalendarEvent, PrivatePersonRef


def _event(
    *,
    event_id: str,
    provider: str,
    provider_event_id: str,
    title: str = "Design review",
    start: datetime | None = None,
    end: datetime | None = None,
    organiser_email: str | None = "alex@example.com",
    organiser_name: str | None = "Alex",
    description: str | None = None,
    attendees: list[PrivatePersonRef] | None = None,
    calendar_id: str | None = None,
) -> PrivateCalendarEvent:
    return PrivateCalendarEvent(
        id=event_id,
        provider=provider,  # type: ignore[arg-type]
        provider_event_id=provider_event_id,
        calendar_id=calendar_id,
        title=title,
        description=description,
        start_at=start or datetime(2026, 8, 16, 14, 0, tzinfo=UTC),
        end_at=end or datetime(2026, 8, 16, 15, 0, tzinfo=UTC),
        organiser=(
            PrivatePersonRef(display_name=organiser_name, email=organiser_email)
            if organiser_email or organiser_name
            else None
        ),
        attendees=attendees or [],
    )


def test_dedupe_passthrough_single_event() -> None:
    event = _event(
        event_id="evt_1",
        provider="apple_calendar",
        provider_event_id="EK-1",
    )
    assert dedupe_calendar_events([event]) == [event]


def test_dual_source_apple_google_same_meeting_collapses() -> None:
    """Synthetic Apple∪Google pair (M08 soft dep — no Apple ingest required)."""
    apple = _event(
        event_id="apple_calendar:EK-1",
        provider="apple_calendar",
        provider_event_id="EK-1",
        calendar_id="cal-personal",
        description=None,
        attendees=[PrivatePersonRef(display_name="Sam", email="sam@example.com")],
    )
    google = _event(
        event_id="google_calendar:primary:evt_design_review",
        provider="google_calendar",
        provider_event_id="evt_design_review",
        calendar_id="primary",
        title="  Design   Review ",
        description="Bring notes",
        attendees=[
            PrivatePersonRef(display_name="Alex", email="alex@example.com"),
            PrivatePersonRef(display_name="Sam", email="sam@example.com"),
        ],
    )
    # Near-identical start (within heuristic window).
    google = google.model_copy(
        update={"start_at": datetime(2026, 8, 16, 14, 1, tzinfo=UTC)}
    )

    deduped = dedupe_calendar_events([apple, google])
    assert len(deduped) == 1
    canonical = deduped[0]
    assert canonical.provider == "google_calendar"
    assert canonical.description == "Bring notes"
    assert len(canonical.attendees) == 2


def test_different_meetings_remain_distinct() -> None:
    morning = _event(
        event_id="g1",
        provider="google_calendar",
        provider_event_id="a",
        title="Standup",
        start=datetime(2026, 8, 16, 9, 0, tzinfo=UTC),
        end=datetime(2026, 8, 16, 9, 15, tzinfo=UTC),
    )
    afternoon = _event(
        event_id="a1",
        provider="apple_calendar",
        provider_event_id="b",
        title="Standup",
        start=datetime(2026, 8, 16, 15, 0, tzinfo=UTC),
        end=datetime(2026, 8, 16, 15, 15, tzinfo=UTC),
    )
    assert len(dedupe_calendar_events([morning, afternoon])) == 2


def test_organiser_mismatch_blocks_collapse() -> None:
    left = _event(
        event_id="g1",
        provider="google_calendar",
        provider_event_id="a",
        organiser_email="alex@example.com",
    )
    right = _event(
        event_id="a1",
        provider="apple_calendar",
        provider_event_id="b",
        organiser_email="other@example.com",
    )
    assert len(dedupe_calendar_events([left, right])) == 2


def test_downstream_attention_evidence_ignores_provider() -> None:
    apple = _event(
        event_id="apple_calendar:EK-1",
        provider="apple_calendar",
        provider_event_id="EK-1",
    )
    google = _event(
        event_id="google_calendar:primary:evt_design_review",
        provider="google_calendar",
        provider_event_id="evt_design_review",
        description="notes",
    )
    [canonical] = dedupe_calendar_events([apple, google])
    evidence_dict = calendar_evidence_from_event(canonical)
    assert "provider" not in evidence_dict
    evidence = CalendarEvidence.model_validate(evidence_dict)
    assert evidence.kind == "calendar"
    assert evidence.event_id == canonical.id
    assert evidence.title == canonical.title
    dumped = evidence.model_dump()
    assert "provider" not in dumped
