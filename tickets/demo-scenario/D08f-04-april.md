# D08f-04 — April ordinary events (quiet / decay)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D08f-04-april` |
| Domain | `demo-scenario` |
| Parent | [D08f](./D08f-alex-six-month.md) |

## Package boundary (hard)

- May edit: `scenarios/alex-v1/timeline/2026-04/**`, `scenarios/alex-v1/content/**` (new bodies only)
- Must not edit: other months’ committed events, `packages/ingestion/**`, C11, SEC-07, `intent_router.py`, Life Scripts

## Hard depends

- [D08f](./D08f-alex-six-month.md) programme

## Soft depends (~)

- [D08f-02](./D08f-02-february.md) loader. Do not block start.
- [SEC-06](../security/SEC-06-retention-memory-decay-forget.md) — clock + sparse events are enough; do not reimplement decay.

## Shape (ordinary)

Quiet. Few new obligations. Old January/February info should be *able* to decay (time gap + no reinforcement). One dormant project (checkout / Atlas-adjacent is fine if already in Jan) becomes relevant again via a mundane ping — not a secret revival plot.

## Non-goals

- Implementing SEC-06 GC · C11 · filling April with as many events as January

## Acceptance criteria

- [ ] Source events only under `timeline/2026-04/`
- [ ] Volume is visibly quieter than March (author fewer events on purpose)
- [ ] One dormant-thread ping with a source id that already existed earlier
- [ ] No world-model keys; no `ALEX_BIOGRAPHY.md`

## Test plan

- After glob: April events load; latest April `at` is in 2026-04
- Count of April events is documented in the month README (order-of-magnitude, not a quota)

## Privacy constraints

- Fictional only. Quiet ≠ empty biography dump.
