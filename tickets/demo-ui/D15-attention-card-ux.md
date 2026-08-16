# D15 — Demo Attention card UX polish

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/D15-attention-card-ux` |
| Domain | `demo-ui` |

## Package boundary (hard)

- May edit: `apps/web/src/demo/**`, demo styles in `apps/web/src/styles.css`
- Must not edit: `packages/attention/**`; demo API pipeline / attention engine surface policy

## Hard depends

- D10, D13

## Soft depends (~)

- D10a (suppressed counts already on attention payload)

## Acceptance criteria

- [x] Attention cards show title + compact priority/timing badges + one short reason sentence + Why?/Done/Snooze
- [x] Evidence dumps (`Reminder: …; Email: …; Calendar: …`) never appear on the card face (Why panel only)
- [x] Header reads like “N things matter now”; optional “Show N that can wait” from `suppressed_count`
- [x] Vitest covers product card copy (no evidence dump; compact header)

## Privacy constraints

- Dashboard stays on private UI names; do not surface PERSON_* on cards
