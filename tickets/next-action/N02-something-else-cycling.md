# N02 — Something-else cycling

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/N02-something-else-cycling` |
| Domain | `next-action` |

## Package boundary (hard)

- May edit: Core/Demo API surfaces that expose next-action candidates; `packages/attention/**` (or next-action package) cycle helpers; tests
- Soft coordinate with [D18](../demo-ui/D18-demo-next-action.md) for Demo chrome — prefer API contract first to avoid large `apps/web` conflicts
- Must not edit: Shadow silence docs; Attention interrupt ranking thresholds

## Hard depends

- M20

## Soft depends (~)

- N01 (better candidate order)
- D18 (UI button wiring)

## Unlocks / enhances

- Soft-unlocks N03 reject events

## Non-goals

- Long-term preference model (N03)
- Infinite scroll of all can-wait items
- Treating reject as “never suggest this category again”

## Acceptance criteria

- [ ] Primary Next Action always accompanied by a Something-else affordance in product contract
- [ ] Something else advances to the next ranked unused candidate in the current suggestion window
- [ ] Cycle includes at least one REST / NOTHING-style candidate when obligations are under control
- [ ] Exhausted cycle either wraps with a soft “that’s the set for now” reason or regenerates with novelty penalty — documented behaviour + test
- [ ] Reject events are emit-able for N03 (event shape stub OK)

## Test plan

- Ordered candidate list → successive Something-else indices
- REST/NOTHING present in cycle under empty-attention fixture

## Privacy constraints

- Cycle payloads use private UI titles/reasons; no PERSON_* or raw emails on the wire to remote models
