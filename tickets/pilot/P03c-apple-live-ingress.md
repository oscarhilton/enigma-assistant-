# P03c — Apple live calendar ingress (operator sync)

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/P03c-apple-live-ingress` |
| Domain | `pilot` |
| Programme | [PILOT-01](./README.md) |
| Parent | [P03](./P03-calendar-read-support.md) (`in_progress` — **not done** until hardware stamp) |
| Depends | [P03a](./P03-calendar-read-support.md) #109, [P03b](./P03b-live-calendar-ingress.md) #110 |

P03b (#110) froze the **store → P03a READ/SUPPORT** contract. P03c adds the missing link:

```text
EventKit → M08 Apple Bridge → AppleCalendarSource → CalendarEventStore.replace_all()
  → existing P03a path → answer + Why
```

## Intent

Operator-triggered Apple sync writes the **complete current Apple snapshot** into My Enigma's private store. The Assistant does **not** gain a `calendar.sync` tool — this is application plumbing, not raised authority.

## Freeze bar

| Must | Must not |
| --- | --- |
| Reuse P03a tools only after sync | Assistant `calendar.sync` or raised authority |
| My Enigma private root only | Alex Lab visibility or shared storage |
| Explicit pilot calendar selection | Settings Palace / OAuth / Google (M12) |
| Operator POST `/worlds/my_enigma/calendar/sync` | Scheduler daemon / worker framework |
| Reduced facts on conversation wire (unchanged) | Durable Life Memory from observation |

## Multi-source assumption (record, do not solve)

P03c `replace_all()` owns the **Apple-only** pilot snapshot. When M12 joins later:

```text
Apple snapshot + Google snapshot → packages/dedupe → one governed store projection
```

Never `replace_all(apple)` then `replace_all(google)` independently.

## Pilot calendar selection

Explicit, private-world-only, inspectable:

- `ENIGMA_PILOT_APPLE_CALENDAR_IDS` — comma-separated EventKit calendar IDs, **or**
- `{private_root}/calendar/pilot_selection.json` — `{"calendar_ids": ["..."]}`

Bridge credentials (development):

- `ENIGMA_BRIDGE_TOKEN` (required for live sync)
- `ENIGMA_BRIDGE_BASE_URL` (optional, default `http://127.0.0.1:8765`)
- `ENIGMA_BRIDGE_UNIX_SOCKET` (optional UDS path)

## Package boundary

- `apps/api/src/personal_enigma/api/private_calendar_sync.py`
- `apps/api/src/personal_enigma/api/routes/worlds.py` (sync route hook only)
- `apps/api/tests/test_p03c_apple_calendar_sync.py`
- `docs/pilot/goose-calibration-hardware.md`
- this ticket, [P03](./P03-calendar-read-support.md), [P03b](./P03b-live-calendar-ingress.md), [README](./README.md)

**Must not edit:** `packages/ingestion/sources/*` (consume `AppleCalendarSource` only).

## CI acceptance

- [x] Mock bridge → events mapped to `PrivateCalendarEvent` → `replace_all` on private root
- [x] Sync route requires My Enigma active; Alex cannot trigger or read private store via sync
- [x] Sync is not an Assistant tool (`calendar.sync` absent from allowed tools)
- [x] Conversation after sync uses store path (no fixture env)
- [x] Sync does not create durable memory / does not mutate on read

## Hardware acceptance (manual — closes P03)

See [goose-calibration-hardware.md](../../docs/pilot/goose-calibration-hardware.md).

- [ ] Create real event **Goose Calibration — tomorrow 14:30**
- [ ] Operator sync → event in `calendar/events.json`
- [ ] “What am I doing tomorrow?” → correct time/title
- [ ] Why → reduced facts, no attendee/description egress
- [ ] Alex Lab → event absent
- [ ] Change to 15:00 → sync → 3pm; delete → sync → gone
- [ ] Three boring questions against actual data
- [ ] Throughout: no writes, no authority raise, no Life Memory from observation

## Test plan

```bash
uv run pytest apps/api/tests/test_p03c_apple_calendar_sync.py
uv run pytest apps/api/tests/test_p03b_live_calendar_ingress.py
```
