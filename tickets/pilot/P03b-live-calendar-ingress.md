# P03b — Live calendar ingress proof

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/P03b-live-calendar-ingress` |
| Domain | `pilot` |
| Programme | [PILOT-01](./README.md) |
| Parent | [P03](./P03-calendar-read-support.md) (`in_progress` — **not done**) |

P03a ([#109](https://github.com/oscarhilton/enigma-assistant-/pull/109), `9f76394`) froze the **fixture/store → reduced facts → Tomorrow/Weekend/Availability** path. P03b proves a **real** calendar event can enter that same path through intended live ingress.

Live hardware (Apple Bridge / Google OAuth) cannot be proven in CI. This ticket stays open until one actual event is observed on a machine with the bridge. The CI slice only proves the production route is **not fixture-only**.

## Intent

One actual event must survive:

```text
real calendar
  → private ingestion (M08 Apple Calendar / M12 Google Calendar, already in architecture)
  → Today / question resolution
  → reduced calendar fact
  → answer
  → Why
```

Exercise the already-frozen #109 path. Do not weaken privacy or authority.

## Freeze bar

**No new UI. No new reasoning. No writes. No Gmail. No cockpit furniture.**

| Must | Must not |
| --- | --- |
| Reuse #109 `agenda.get` / `availability.check` / `world.explain` | Add `assist.*`, `source.*`, Gmail, calendar create/update/delete |
| Store under My Enigma private root (`calendar/events.json`) | Share Demo / Alex Lab storage or HMAC |
| Reduced facts only (title, time, id) on the reasoning wire | Egress raw description / attendee emails unnecessarily |
| READ/SUPPORT remains the authority ceiling | Promote a hold into a booking or durable memory |
| Disk store is source of truth after ingest | Require `ENIGMA_CALENDAR_FIXTURE` in production |
| World switch clears derived conversation / AgentWork (ADR-040) | Leave calendar-derived UI after switching to Alex |

## Package boundary

- `apps/api/src/personal_enigma/api/private_calendar_store.py`
- `apps/api/tests/test_p03b_live_calendar_ingress.py`
- `tickets/pilot/P03-calendar-read-support.md`
- `tickets/pilot/P03b-live-calendar-ingress.md`
- `tickets/pilot/README.md`
- `docs/adr/041-my-enigma-calendar-read-ceiling.md` (P03b note only)

**Must not edit:** `packages/ingestion/sources/*` (M08/M12 ownership), web UI, Goose, Gmail, assist tools, Alex Lab demo sources.

## Hard depends

- P03a merged (#109)
- Live proof additionally needs a machine with M08 Apple Bridge and/or M12 Google Calendar credentials (not available in CI)

## CI-provable slice (this PR)

Prove live ingestion **would** use `StoreCalendarAdapter` without a fixture:

- [x] `calendar_adapter_for_root` returns `StoreCalendarAdapter` when `ENIGMA_CALENDAR_FIXTURE` is unset
- [x] Production conversation route answers Tomorrow from `calendar/events.json` on the private world root — **no fixture env**
- [x] Changing or deleting the store file is reflected on the next read (disk is source of truth)
- [x] Asking a question does not mutate the store (observation is not memory)
- [x] Reduced facts still strip description/attendees on the store path
- [x] Alex cannot read My Enigma calendar provenance

## Hardware slice (not in CI — leave open)

- [ ] One real event: Apple or Google calendar → private store → “What am I doing tomorrow?” → reduced fact in Why
- [ ] Same event invisible in Alex Lab
- [ ] Source refresh does not create durable memory merely by being observed
- [ ] Deleting/changing the live source is reflected after the next ingest
- [ ] World switch clears derived UI / AgentWork
- [ ] Three boring questions against actual data: tomorrow / this weekend / am I free Monday?

## Test plan

```bash
uv run pytest apps/api/tests/test_p03b_live_calendar_ingress.py
```

## Non-goals

Worker/bridge wiring that writes M08/M12 batches into `calendar/events.json` is the remaining hardware slice — do not expand this ticket into a new sync job, UI, or LLM planner.
