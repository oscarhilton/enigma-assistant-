# M09 — Apple Reminders

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M09-apple-reminders` |
| Domain | `apple-bridge` |

## Package boundary (hard)

- May edit: `apps/apple-bridge` Reminders module + routes
- May edit: `packages/ingestion` Apple reminders source
- Attention wiring only via emitting `PrivateReminder` (no M15 merge yet)

## Depends on

- M01, M07

## Unlocks

- M06 signal quality, M15

## Non-goals

- Creating/updating reminders (explicitly outside v0.1)
- Todoist / other task providers

## Acceptance criteria

- [ ] Read-only EventKit reminders access
- [ ] Ingest incomplete reminders with due dates
- [ ] Map to `PrivateReminder` (`provider="apple_reminders"`)
- [ ] `GET /reminders/changes` with cursor
- [ ] Explicit reminders treated as first-class intent signals in docs/tests

## Test plan

- Mapping unit tests
- Completed vs incomplete filtering tests for MVP defaults

## Privacy constraints

- MVP read-only
