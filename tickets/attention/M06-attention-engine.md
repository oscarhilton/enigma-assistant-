# M06 — Attention engine

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M06-attention-engine` |
| Domain | `attention` |

## Package boundary (hard)

- May edit: `packages/attention/**`
- May read: domain, fixtures, transformation
- Worker wiring allowed only for invoking the engine

## Depends on

- M01, M02; M03 recommended

## Unlocks

- M15, M16

## Non-goals

- Full cross-source merge algorithm (M15)
- UI polish

## Acceptance criteria

- [ ] Distinguishes `INFERRED_OBLIGATION`, `EXPLICIT_REMINDER`, `INFERRED_COMMITMENT`, `CALENDAR_OBLIGATION`
- [ ] Explicit reminders outrank weak email inferences when competing
- [ ] Produces ranked `AttentionItem` list from fixture scenarios
- [ ] Works with remote LLM disabled (local heuristics acceptable for v0)

## Test plan

- Fixture scenarios with known expected top attention item
- Ordering tests for reminder vs inferred commitment

## Privacy constraints

- Attention items shown to user may use local names; anything sent remote must already be transformed
