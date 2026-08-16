# M12 — Google Calendar

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M12-google-calendar` |
| Domain | `google` |

## Package boundary (hard)

- May edit: google calendar source under ingestion / new google package
- May edit: dedupe helpers (prefer `packages/ingestion` or small `packages/dedupe`)
- Coordinate with M08 for dual-ingest fixtures — do not rewrite Apple bridge

## Depends on

- M01, M08 recommended for dedupe tests

## Unlocks

- M15 calendar evidence without duplicates

## Non-goals

- Write events
- Blind import of all calendars without user selection

## Acceptance criteria

- [ ] Read-only Google Calendar API → `PrivateCalendarEvent` (`provider="google_calendar"`)
- [ ] User calendar selection
- [ ] Deduplicate against Apple-ingested same events (one canonical event)
- [ ] Downstream ignores provider for attention

## Test plan

- Dual-source fixture: same meeting via Google + Apple → one event
- Selection tests exclude unchecked calendars

## Privacy constraints

- Medium; organiser/attendees resolved to PERSON ids before remote
