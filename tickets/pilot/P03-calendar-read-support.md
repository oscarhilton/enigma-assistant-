# P03 — First real source: Calendar READ + SUPPORT

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/P03-calendar-read-support` (P03a) · `ticket/P03b-live-calendar-ingress` (P03b) |
| Domain | `pilot` |
| Programme | [PILOT-01](./README.md) |

**Not done.** Fixture/store vertical path landed as P03a; live ingress is [P03b](./P03b-live-calendar-ingress.md). Do not mark “real Tuesday complete”.

## Intent

Connect **exactly one** real thing to My Enigma: Calendar.

Pilot authority:

- **READ**
- **SUPPORT**
- **No calendar writes** initially

Then the product can actually answer:

- “What am I doing tomorrow?”
- “What's coming up this weekend?”
- “Am I actually free Monday?”
- “What's worth my attention?”

Every next capability after this has to earn itself from a real annoyance.

## Slices

### P03a — Calendar READ/SUPPORT vertical path (fixture/store) — merged

[#109](https://github.com/oscarhilton/enigma-assistant-/pull/109) (`9f76394`). Frozen path:

`fixture or private store → reduced calendar facts → Tomorrow / Weekend / Availability`

No new UI. No new reasoning. No writes. No Gmail.

### P03b — Store ingress contract — done

[#110](https://github.com/oscarhilton/enigma-assistant-/pull/110) (`264a331`). Production store path is not fixture-only; disk reload + isolation tests.

### P03c — Apple live ingress — in progress

[P03c](./P03c-apple-live-ingress.md). Operator-triggered M08 sync → `calendar/events.json` → frozen P03a path. Hardware proof: [goose-calibration-hardware.md](../../docs/pilot/goose-calibration-hardware.md).

## Package boundary (when claimed)

- My Enigma world only (`EnvironmentMode.PRIVATE`)
- Apple Calendar and/or Google Calendar **read** adapters already in-tree (M08 / M12)
- Must not enable calendar writes, Gmail, or Settings Palace

## Hard depends

- [P01](./P01-world-isolation-pilot-shell.md) `done`
- SEC-05 personal-data pilot gate before any **mail** (not required to start calendar-read if SEC programme agrees calendar is the bounded first source)

## Privacy constraints

- No calendar writes
- No wholesale attendee emails to hosted models
- Storage stays on the My Enigma private root; never Demo

## Acceptance criteria

### P03a (#109)

- [x] Fixture/store events enter only through My Enigma (`ENIGMA_CALENDAR_FIXTURE` or private store under world root)
- [x] Alex Lab remains synthetic and deterministic (unchanged)
- [x] Calendar descriptions/attendees aren't sprayed into remote prompts by default (`reduced_calendar_fact`)
- [x] Only request-relevant reduced facts reach reasoning
- [x] Calendar event existence is NOT promoted into stronger claims
- [x] READ/SUPPORT cannot create or mutate calendar state (authority ceiling + write refusal)
- [x] Switching worlds clears calendar-derived conversation state (ADR-040)
- [x] Why can show what calendar facts were used (`/worlds/my_enigma/calendar/provenance`)
- [x] Goose movement remains projection-only (no P03 Goose changes)
- [x] No standing background calendar agent
- [x] Three pilot scripts: Tomorrow, Weekend, Monday availability (API + browser tests)

### P03b (live)

- [x] Production conversation route does not require `ENIGMA_CALENDAR_FIXTURE` when store events exist (#110)
- [ ] Hardware stamp — see P03c + [goose-calibration-hardware.md](../../docs/pilot/goose-calibration-hardware.md)

## Test plan

- `uv run pytest apps/api/tests/test_p03_calendar_read_support.py`
- `pnpm exec vitest run src/pilot/CalendarReadProduct.test.tsx`
- P03b: `uv run pytest apps/api/tests/test_p03b_live_calendar_ingress.py`
- P03c: `uv run pytest apps/api/tests/test_p03c_apple_calendar_sync.py`

## Dogfood (after hardware stamp)

When [goose-calibration-hardware.md](../../docs/pilot/goose-calibration-hardware.md) passes:

- Use **My Enigma** daily for schedule questions (READ/SUPPORT only)
- Watch C37 telemetry for Goose legibility with real AgentWork
- **C36 remains unclaimed**
- No Gmail, no calendar writes, no Settings cathedral

Hardware observation pending: `apps/api/tests/fixtures/goose_observation/p03_hardware_pending.yaml`

## PR

- P03a: [#109](https://github.com/oscarhilton/enigma-assistant-/pull/109) merged `9f76394`
- P03b: [#110](https://github.com/oscarhilton/enigma-assistant-/pull/110) merged `264a331`
- P03c: see [P03c](./P03c-apple-live-ingress.md)
