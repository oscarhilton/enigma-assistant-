# Goose Calibration — P03 hardware proof

Manual checklist to close [P03](../tickets/pilot/P03-calendar-read-support.md) after [P03c](../tickets/pilot/P03c-apple-live-ingress.md) merges. CI cannot run EventKit.

## Prerequisites

- macOS with Apple Bridge running locally (`apps/apple-bridge`)
- `ENIGMA_BRIDGE_TOKEN` matches bridge bearer secret
- `ENIGMA_PILOT_APPLE_CALENDAR_IDS` set to permitted EventKit calendar ID(s)
- Enigma API + web pilot shell (My Enigma world)

## Setup

1. Create a real calendar event: **Goose Calibration** — tomorrow at **14:30** (30 min).
2. Switch product world to **My Enigma**.
3. Ensure `ENIGMA_CALENDAR_FIXTURE` is **unset**.

## Sequence

| Step | Action | Expected |
| --- | --- | --- |
| 1 | `POST /worlds/my_enigma/calendar/sync` | `ok: true`, `event_count >= 1` |
| 2 | Inspect `~/.enigma/private/calendar/events.json` | Goose Calibration present with correct time |
| 3 | Ask: “What am I doing tomorrow?” | Title + ~2:30pm (local formatting ok) |
| 4 | `GET /worlds/my_enigma/calendar/provenance` | Event id/title/time; **no** attendee emails or description body |
| 5 | Switch to **Alex Lab** | Goose Calibration **absent** from conversation/demo |
| 6 | Change event to **15:00** in Calendar.app | — |
| 7 | Sync again → ask tomorrow | ~3:00pm |
| 8 | Delete event in Calendar.app | — |
| 9 | Sync again → ask tomorrow | No Goose Calibration / nothing scheduled |
| 10 | “What's coming up this weekend?” | Matches your real calendar (reduced facts) |
| 11 | “Am I free Monday?” | Honest availability from real data |

## Invariants (throughout)

- [ ] No calendar **writes** performed by Enigma
- [ ] Assistant authority remains **READ / SUPPORT** only
- [ ] No durable **Life Memory** created merely from sync or asking
- [ ] Alex Lab cannot see My Enigma calendar data
- [ ] World switch clears calendar-derived conversation / AgentWork (ADR-040)
- [ ] No unnecessary remote egress of descriptions / attendees

## Record results

```yaml
scenario: goose_calibration_hardware
observed:
  sync_event_count: ...
  tomorrow_reply: ...
  provenance_ok: true/false
  alex_isolated: true/false
problem: true/false
severity: ...
possible_fix: NOT YET  # or ticket reference if blocking P03 close
```

When all steps pass, mark P03 **done** in `tickets/pilot/P03-calendar-read-support.md`.
