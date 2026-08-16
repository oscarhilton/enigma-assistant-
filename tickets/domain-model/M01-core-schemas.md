# M01 — Core schemas

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/M01-core-schemas` |
| Domain | `domain-model` |

## Package boundary (hard)

- May edit: `packages/domain/**` only
- Must not edit: other packages/apps (except doc links)

## Hard depends

- None (scaffold stubs exist)

## Soft depends (~)

- None

## Unlocks / enhances

- Hard-unlocks M02, M03, M04, M00a, and all ingestion tickets that consume domain types

## Non-goals

- Persistence / database migrations (M00a)
- Provider adapters
- Transformation or attention logic
- Entity resolver implementation (M10 / `packages/identity`)

## Acceptance criteria

- [x] `SourceType` and `Provider` enums match architecture docs
- [x] `PrivateCalendarEvent` includes calendar name, URL, availability, and all Apple-addendum fields
- [x] `PrivateReminder`, `PrivatePerson`, `PrivatePersonRef`, `PrivateNote`, `RecurrenceInfo` complete per addendum
- [x] `PrivateMessage` exists for Gmail / future mail providers
- [x] Typed obligation evidence: `ReminderEvidence`, `EmailEvidence`, `CalendarEvidence`, `NoteEvidence`
- [x] Models validate with Pydantic v2; serialization round-trips in tests
- [x] Provider-specific fields stay on edge models only

## Test plan

- Unit tests for required fields, literals, and datetime handling
- Round-trip `model_dump` / `model_validate` for each model including evidence discriminators

## Privacy constraints

- Models are private-local; no remote DTOs in this package
