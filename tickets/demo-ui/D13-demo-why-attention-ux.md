# D13 — Demo Why + Attention UX polish

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/demo-why-attention-ux` |
| Domain | `demo-ui` |

## Package boundary (hard)

- May edit: `apps/web/src/demo/**`, demo styles in `apps/web/src/styles.css`
- May edit: `apps/api` demo control routes (`/demo/*`) as needed for structured attention/why payloads
- May edit: short docs note under `docs/demo/` or `docs/architecture/` for representation layers
- Must not edit: privacy transform packages; scenario corpus (D8)

## Hard depends

- D10

## Soft depends (~)

- None

## Acceptance criteria

- [x] Why view: Evidence → Inference → Decision → Why now?; priority vs confidence split; richer Atlas copy; reason codes as machine layer
- [x] Attention dashboard: product promise header + secondary scenario line; WHAT/WHEN/KIND/Priority/Confidence; private UI names; human summaries; Done/Snooze; sort by attention rank; footer surfaced/suppressed when available
- [x] Three representation layers documented (PRIVATE UI / MODEL VIEW / EXTERNAL ATTENTION)
- [x] Vitest + API tests cover copy/structure

## Privacy constraints

- Do not weaken privacy transforms
- Dashboard uses private UI names; Why may show model-view pseudonyms
