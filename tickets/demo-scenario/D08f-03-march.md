# D08f-03 — March ordinary events

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D08f-03-march` |
| Domain | `demo-scenario` |
| Parent | [D08f](./D08f-alex-six-month.md) |

## Package boundary (hard)

- May edit: `scenarios/alex-v1/timeline/2026-03/**`, `scenarios/alex-v1/content/**` (new bodies only)
- Must not edit: `timeline/week-*.yaml`, January/February files, `packages/ingestion/**`, C11, SEC-07, `intent_router.py`, Life Scripts

## Hard depends

- [D08f](./D08f-alex-six-month.md) programme

## Soft depends (~)

- [D08f-02](./D08f-02-february.md) (loader + 0.3.0). **Do not block start** — nested YAML is safe to author before the glob lands.

## Shape (ordinary)

Busier than February. One calendar conflict. One waiting-on. Something rescheduled **twice**. A weak intention (note / casual message) must **not** become a task — no reminder.upsert that would force Enigma to treat it as an obligation; ground truth (later) should expect suppression.

## Non-goals

- Other months’ content · C11 · WhatsApp runtime · cinematic plot · Life Script YAML

## Acceptance criteria

- [ ] Source events only under `timeline/2026-03/`
- [ ] Calendar conflict + waiting-on + double reschedule are evidenced, not narrated in a bio file
- [ ] Weak intention is a note or mail snippet **without** a matching reminder
- [ ] No world-model keys; no `ALEX_BIOGRAPHY.md`

## Test plan

- After D08f-02 glob: March events load; ids unique vs other months
- Feature-pack style: calendar-conflict already exists under `scenarios/feature/` — this is Alex-continuous, not a duplicate feature pack

## Privacy constraints

- Fictional only. Existing source types only.
