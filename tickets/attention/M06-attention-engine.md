# M06 — Attention engine

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/M06-attention-engine` |
| Domain | `attention` |

## Package boundary (hard)

- May edit: `packages/attention/**` only
- May read: domain, fixtures, transformation
- Must not edit: obligation merge package logic reserved for M15 beyond exporting attention kinds

## Hard depends

- M01

## Soft depends (~)

- M02 (scenarios)
- M03 (transformed inputs)
- M09 (richer explicit-reminder signals later — **do not wait**)

## Unlocks / enhances

- Hard-unlocks M15 ranking inputs

## Non-goals

- Full cross-source merge algorithm (M15)
- UI polish
- Remote LLM ranking (optional later via M05)

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
