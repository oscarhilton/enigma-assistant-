# M12 — Google Calendar

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M12-google-calendar` |
| Domain | `google` |

## Package boundary (hard)

- May edit: `packages/ingestion/src/personal_enigma/ingestion/sources/google_calendar.py`
- May edit: `packages/dedupe/**`
- May edit: `apps/api/src/personal_enigma/api/google/calendar/**` and `apps/worker/src/personal_enigma/worker/google/calendar/**` (create)
- May edit: `apps/web/src/settings/calendars/google/**` (create) for Google calendar selection only
- Must not edit: Apple bridge Calendar module, `sources/apple_*.py`

## Hard depends

- M01

## Soft depends (~)

- M08 (dual-source dedupe fixtures — implement Google ingest first; add Apple∪Google tests when M08 exists)
- M00b

## Unlocks / enhances

- Calendar evidence without duplicates for M15

## Non-goals

- Write events
- Blind import of all calendars without user selection
- Rewriting Apple EventKit code

## Acceptance criteria

- [ ] Read-only Google Calendar API → `PrivateCalendarEvent` (`provider="google_calendar"`)
- [ ] User calendar selection
- [ ] `dedupe_calendar_events` collapses Google∪Apple duplicates to one canonical event
- [ ] Downstream attention ignores provider

## Test plan

- Dual-source fixture: same meeting via Google + Apple → one event (skip Apple side until M08)
- Selection tests exclude unchecked calendars

## Privacy constraints

- Medium; organiser/attendees resolved to PERSON ids before remote
