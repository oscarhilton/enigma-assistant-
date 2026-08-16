# M08 — Apple Calendar

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/M08-apple-calendar` |
| Domain | `apple-bridge` |

## Package boundary (hard)

- May edit: `apps/apple-bridge/Sources/EnigmaAppleBridgeCore/Calendar/**`
- May edit: Transport routes **only** for `/calendar/*` under `.../Transport/**`
- May edit: `packages/ingestion/src/personal_enigma/ingestion/sources/apple_calendar.py`
- May edit: `apps/web/src/settings/calendars/**` (create) for Apple calendar selection UI only
- Must not edit: other `sources/*.py`, `packages/dedupe/**` (M12), Reminders/Contacts/Notes modules

## Hard depends

- M01, M07

## Soft depends (~)

- M00b (settings shell)
- M02 (mapping fixtures)

## Unlocks / enhances

- Enables M12 dual-source dedupe tests
- Supplies calendar evidence for M15

## Non-goals

- Write/edit calendar events
- Google Calendar (M12)
- Implementing `packages/dedupe` (M12 owns it; M08 emits canonical events only)

## Acceptance criteria

- [x] Request **read-only** EventKit calendar access
- [x] Ingest selected calendars only
- [x] Map required fields including calendar name, URL, availability, organiser, attendees, recurrence, last modified
- [x] Emit `PrivateCalendarEvent` with `provider="apple_calendar"`
- [x] `GET /calendar/changes` with cursor support

## Test plan

- Unit tests for EKEvent → canonical mapping with fixtures/mocks
- Permission-denied path returns authorised=false without crashing Core

## Privacy constraints

- Read-only; no remote send of raw events from bridge
