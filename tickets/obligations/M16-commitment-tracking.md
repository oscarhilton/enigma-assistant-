# M16 — Commitment tracking

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/M16-commitment-tracking` |
| Domain | `obligations` |

## Package boundary (hard)

- May edit: `packages/obligations/**` and/or `packages/attention/**` commitment modules
- May edit: persistence hooks only under paths introduced by M00a
- Must not edit: Gmail adapter (M11), Apple Bridge sources

## Hard depends

- M15

## Soft depends (~)

- M11 (email commitments — **Apple reminder/calendar commitments must work without Gmail**)
- M13 / M14 (deferred Notes tasks)
- M00a

## Unlocks / enhances

- Richer temporal attention

## Non-goals

- Full CRM
- Sending follow-up emails

## Acceptance criteria

- [x] Track inferred commitments vs explicit reminders
- [x] Update state when evidence appears (follow-up email, completed reminder, elapsed due date)
- [x] Surface stale commitments in attention engine
- [x] Notes deferred-task pattern supported when M13/M14 present
- [x] MVP path works with Apple-only evidence (no Gmail required)

## Test plan

- Temporal fixture timelines (Apple-only and Apple+Gmail)
- State machine unit tests

## Privacy constraints

- Commitment text stored locally; remote sees sanitised summaries
