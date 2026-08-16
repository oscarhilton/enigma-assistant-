# M02 — Synthetic fixture pipeline

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M02-synthetic-fixture-pipeline` |
| Domain | `fixtures` |

## Package boundary (hard)

- May edit: `packages/fixtures/**`
- May read: `packages/domain/**`
- Must not edit: adapters, API, bridge

## Depends on

- M01

## Unlocks

- M03, M04, M06, M15 (deterministic tests without live Apple/Google)

## Non-goals

- Live API calls
- Production database seeding scripts beyond fixtures

## Acceptance criteria

- [ ] Fixture builders for calendar events, reminders, contacts, notes, and email-like messages
- [ ] Scenario packs that encode cross-source obligation cases (reminder + email + calendar)
- [ ] Fixtures are deterministic and documented
- [ ] Pipeline can load scenarios into in-memory stores used by tests

## Test plan

- Snapshot / equality tests for scenario packs
- Smoke test that fixtures construct valid domain models

## Privacy constraints

- Fixtures must not contain real personal data; synthetic only
