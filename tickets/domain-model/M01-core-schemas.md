# M01 — Core schemas

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M01-core-schemas` |
| Domain | `domain-model` |

## Package boundary (hard)

- May edit: `packages/domain/**`
- May edit tests: `packages/domain/tests/**`
- Must not edit: other packages/apps (except doc links)

## Depends on

- None (scaffold already has stub models)

## Unlocks

- M02, M03, M04, and all ingestion tickets

## Non-goals

- Persistence / database migrations
- Provider adapters
- Transformation or attention logic

## Acceptance criteria

- [ ] `SourceType` and `Provider` enums match architecture docs
- [ ] `PrivateCalendarEvent`, `PrivateReminder`, `PrivatePerson`, `PrivatePersonRef`, `PrivateNote`, `RecurrenceInfo`, `Obligation` are complete per Apple addendum fields
- [ ] Models validate with Pydantic v2; serialization round-trips in tests
- [ ] Provider-specific fields stay on edge models only

## Test plan

- Unit tests for required fields, literals, and datetime handling
- Round-trip `model_dump` / `model_validate` for each model

## Privacy constraints

- Models are private-local; no remote DTOs in this package
