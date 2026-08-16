# M08 — Apple Calendar

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M08-apple-calendar` |
| Domain | `apple-bridge` |

## Package boundary (hard)

- May edit: `apps/apple-bridge/Sources/**/Calendar/**`, Transport routes for calendar
- May edit: `packages/ingestion` Apple calendar source adapter mapping to `PrivateCalendarEvent`
- May edit: `apps/web` settings for calendar selection UI minimally

## Depends on

- M01, M07

## Unlocks

- M12 dedupe interplay, M15

## Non-goals

- Write/edit calendar events
- Google Calendar (M12)

## Acceptance criteria

- [ ] Request **read-only** EventKit calendar access
- [ ] Ingest selected calendars only
- [ ] Map required fields: id, calendar id/name, title, start/end, all-day, location, notes, URL, organiser, attendees, availability, recurrence, last modified
- [ ] Emit `PrivateCalendarEvent` with `provider="apple_calendar"`
- [ ] `GET /calendar/changes` with cursor support

## Test plan

- Unit tests for EKEvent → canonical mapping with fixtures/mocks
- Permission-denied path returns authorised=false without crashing Core

## Privacy constraints

- Read-only; no remote send of raw events from bridge
