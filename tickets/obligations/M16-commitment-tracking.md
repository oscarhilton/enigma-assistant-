# M16 — Commitment tracking

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M16-commitment-tracking` |
| Domain | `obligations` |

## Package boundary (hard)

- May edit: obligations / attention packages
- May persist via api/worker storage layer if introduced here

## Depends on

- M15, M11 (email commitments)

## Unlocks

- Richer attention over time

## Non-goals

- Full CRM
- Sending follow-up emails

## Acceptance criteria

- [ ] Track inferred commitments (“I’ll send that tomorrow”) vs explicit reminders
- [ ] Update state when evidence appears (follow-up email, completed reminder, elapsed due date)
- [ ] Surface stale commitments in attention engine
- [ ] Notes deferred-task pattern supported when M13/M14 present (prerequisite completed)

## Test plan

- Temporal fixture timelines
- State machine unit tests

## Privacy constraints

- Commitment text stored locally; remote sees sanitised summaries
