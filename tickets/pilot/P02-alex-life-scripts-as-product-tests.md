# P02 — Replay Alex Life Scripts as browser-level product tests

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/P02-alex-life-scripts-as-product-tests` |
| Domain | `pilot` |
| Programme | [PILOT-01](./README.md) |

**Do not claim until P01 is `done`.** Do not implement in P01.

## Intent

The first Life Scripts are not new features. They are things we already know are nasty, replayed through the **actual app** as browser-level product tests (not merely architecture / evaluation tests):

| Script | What it proves |
| --- | --- |
| Brunch | talked about ≠ calendar ≠ booked |
| Monday/Maya | challenge premise without inventing truth |
| HONK HONK | relational bootstrap survives the UI boundary |
| Verification failure | acting ≠ completed |
| Forget | memory disappears correctly |
| C37 Goose scenarios | pixels correspond to actual AgentWork |

That class of bug: “architecturally correct, but I have absolutely no idea what the UI is telling me.”

## Package boundary (when claimed)

- Browser product tests against the **same** pilot shell as P01
- Must not invent a second Alex frontend
- Must not implement C36

## Hard depends

- [P01](./P01-world-isolation-pilot-shell.md) `done`
- C12 Life Scripts CLI (`landed`)
- C37 observational infrastructure (`done`) — `possible_fix: NOT YET` stays until evidence says otherwise

## Non-goals

- New Goose motions, Shadows, speech, affection
- Connecting Oscar’s mailbox
- Calendar writes
