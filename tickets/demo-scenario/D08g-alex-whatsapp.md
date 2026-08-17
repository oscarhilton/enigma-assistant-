# D08g — Alex WhatsApp overlay

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/D08g-alex-whatsapp` |
| Domain | `demo-scenario` |

Do **not** confuse with [D08f](./D08f-alex-six-month.md) (six-month ordinary life / 0.3.0). This is a **0.2.2** additive WhatsApp overlay on January weeks.

## Package boundary (hard)

- May edit: `scenarios/alex-v1/**` (contacts phones, `timeline/week-03-whatsapp*.yaml`, ground_truth evidence ids, version `0.2.2`)
- Must not edit: brunch Saturday due date / `cal-brunch-parents` start, D08f nested month dirs, `packages/simulation` engine

## Acceptance criteria

- [x] Elena 1:1 confirms parents + Alex sorts brunch + reaction
- [x] Soft intention, ambiguous chatter, waiting-on, cancellation, correction, group noise
- [x] Cancellation/correction do **not** retarget brunch Saturday
- [x] No Elena biography beyond existing roster + synthetic phone
- [x] Ground truth `obligation_brunch_book` gains chat evidence ids
