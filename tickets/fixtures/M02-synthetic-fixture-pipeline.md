# M02 — Synthetic fixture pipeline

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/M02-synthetic-fixture-pipeline` |
| Domain | `fixtures` |

## Package boundary (hard)

- May edit: `packages/fixtures/**` only
- May read: `packages/domain/**`
- Must not edit: adapters, API, bridge

## Hard depends

- M01

## Soft depends (~)

- None

## Unlocks / enhances

- Hard-unlocks deterministic tests for M03, M04, M06, M15 without live Apple/Google

## Non-goals

- Live API calls
- Production database seeding beyond fixtures

## Acceptance criteria

- [x] Fixture builders for calendar events, reminders, contacts, notes, and messages
- [x] Scenario packs that encode cross-source obligation cases (reminder + email + calendar)
- [x] Fixtures are deterministic and documented
- [x] Pipeline can load scenarios into in-memory stores used by tests

## Test plan

- Snapshot / equality tests for scenario packs
- Smoke test that fixtures construct valid domain models

## Privacy constraints

- Fixtures must not contain real personal data; synthetic only
