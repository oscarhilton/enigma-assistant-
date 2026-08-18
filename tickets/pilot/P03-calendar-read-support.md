# P03 — First real source: Calendar READ + SUPPORT

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/P03-calendar-read-support` |
| Domain | `pilot` |
| Programme | [PILOT-01](./README.md) |

**Do not claim until P01 is `done`.** Do not implement in P01. Do not start Gmail here.

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
