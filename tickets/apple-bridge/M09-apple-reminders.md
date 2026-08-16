# M09 — Apple Reminders

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/M09-apple-reminders` |
| Domain | `apple-bridge` |

## Package boundary (hard)

- May edit: `apps/apple-bridge/Sources/EnigmaAppleBridgeCore/Reminders/**`
- May edit: Transport routes **only** for `/reminders/*`
- May edit: `packages/ingestion/src/personal_enigma/ingestion/sources/apple_reminders.py`
- Must not edit: other sources, attention package (beyond docs), Calendar/Contacts/Notes modules

## Hard depends

- M01, M07

## Soft depends (~)

- M02

## Unlocks / enhances

- Soft-enhances M06 explicit-reminder ranking quality (**M06 must not wait on this ticket**)
- Supplies reminder evidence for M15

## Non-goals

- Creating/updating reminders (outside v0.1)
- Todoist / other task providers
- Obligation merging (M15)

## Acceptance criteria

- [x] Read-only EventKit reminders access
- [x] Ingest incomplete reminders with due dates
- [x] Map to `PrivateReminder` (`provider="apple_reminders"`)
- [x] `GET /reminders/changes` with cursor
- [x] Explicit reminders documented as first-class intent signals in tests

## Test plan

- Mapping unit tests
- Completed vs incomplete filtering tests for MVP defaults

## Privacy constraints

- MVP read-only
