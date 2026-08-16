# D18 — Demo Next Action (worth doing) beside Attention

| Field | Value |
| --- | --- |
| Status | `done` (PR #72) |
| Branch | `ticket/demo-next-action` |
| Domain | `demo-ui` |

## Package boundary (hard)

- May edit: `apps/web/src/demo/**`, demo styles in `apps/web/src/styles.css`, brief note in `docs/architecture/attention-surface.md`, this ticket + `tickets/README.md` demo-ui index line
- Must not edit: `packages/attention/**` ranking; Shadow silence evaluation docs; domain NextAction schema ownership (M20); demo clock/timeline engine

## Hard depends

- D17

## Soft depends (~)

- D10a
- M20 (canonical types; Demo may stub TS shapes until API wired)
- [next-action.md](../../docs/architecture/next-action.md)

## Acceptance criteria

- [x] Product split: ATTENTION (may be empty) · NEXT ACTION (never empty, optional) · CAN WAIT
- [x] Non-empty: NEXT derived from top attention item when sensible (not a second Attention card)
- [x] Empty: NEXT / YOU COULD + I’ll do that / Something else (cycles; includes rest/do nothing)
- [x] Walk/junk never presented as HIGH PRIORITY Attention
- [x] Demo fixtures/stubs always supply at least one next action
- [x] Freeze doc notes three levels: NEEDS YOU / WORTH DOING / CAN WAIT
- [x] Vitest covers empty + non-empty next-action copy/UI

## Privacy constraints

- Dashboard stays on private UI names; do not surface PERSON_* on cards
