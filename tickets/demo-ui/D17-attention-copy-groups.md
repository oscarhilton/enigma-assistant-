# D17 — Demo Attention copy, empty silence, can-wait groups

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/demo-attention-copy-groups` |
| Domain | `demo-ui` |

## Package boundary (hard)

- May edit: `apps/web/src/demo/**`, demo styles in `apps/web/src/styles.css`, `docs/architecture/attention-surface.md`, this ticket + `tickets/README.md` demo-ui index line
- Must not edit: `packages/attention/**`; demo clock / timeline engine; unrelated API routes

## Hard depends

- D15

## Soft depends (~)

- D10a (suppressed counts)

## Acceptance criteria

- [x] Headline: “N things need your attention” (singular / empty silence copy unchanged)
- [x] Card reason is one natural sentence (prefer body / obligation fields; never evidence dumps)
- [x] Empty state: no Refresh CTA; holding-signals sentence always visible; “Show N that can wait” / “Hide what can wait”; “Last evaluated …” secondary line
- [x] Expanded can-wait shows category counts (not 47 mini-cards); optional drill-down
- [x] Doc note: Demo attention surface + empty silence shape frozen; Done/Snooze Demo/Assisted only
- [x] Vitest covers headline, reasons, empty silence, grouped can-wait

## Privacy constraints

- Dashboard stays on private UI names; do not surface PERSON_* on cards
