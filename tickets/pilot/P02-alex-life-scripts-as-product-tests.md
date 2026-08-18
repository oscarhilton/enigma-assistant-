# P02 — Replay Alex Life Scripts as browser-level product tests

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/P02-product-life-scripts` |
| Domain | `pilot` |
| Programme | [PILOT-01](./README.md) |

**Do not claim until P01 is `done`.** Do not implement in P01.

## Intent

The first Life Scripts are not new features. They are things we already know are nasty, replayed through the **actual app** as browser-level product tests (not merely architecture / evaluation tests):

| Script | What it proves |
| --- | --- |
| Brunch (P02a) | talked about ≠ calendar ≠ booked |
| Monday/Maya (P02b) | challenge premise without inventing truth |
| HONK HONK (P02c) | relational bootstrap survives the UI boundary |
| Verification failure (P02d) | acting ≠ completed |
| Forget (P02e) | memory disappears correctly |
| C37 Goose scenarios | pixels correspond to actual AgentWork |

That class of bug: “architecturally correct, but I have absolutely no idea what the UI is telling me.”

Play-shaped scripts live under [apps/web/src/pilot/life-scripts/](../../apps/web/src/pilot/life-scripts/).

## Package boundary (when claimed)

- Browser product tests against the **same** pilot shell as P01
- Must not invent a second Alex frontend
- Must not implement C36
- Must not modify frozen C23 gate (`alex_jan19_continuity_integrity`)

## Hard depends

- [P01](./P01-world-isolation-pilot-shell.md) `done`
- C12 Life Scripts CLI (`landed`)
- C37 observational infrastructure (`done`) — `possible_fix: NOT YET` stays until evidence says otherwise

## Non-goals

- New Goose motions, Shadows, speech, affection
- Connecting Oscar’s mailbox
- Calendar writes

## Acceptance criteria

- [x] **P02a Brunch** — pilot shell: Alex Lab → Jan 20 → unresolved brunch → Case → “what did I book?” → calendar hold ≠ reservation → Goose/Why (merged #107)
- [x] Same app shell as P01 — no second Alex frontend
- [x] **P02b Monday/Maya** — bank holiday discovery, QUALIFIES premise, continuity, AgentWork trail, context-only case
- [x] **P02c HONK HONK** — recognition → serious frame suppression → recovery through shell
- [x] **P02d Verification failure** — PREPARE → APPROVE → ACTING → VERIFYING → fail; return ≠ Done
- [x] **P02e Forget** — retain → recall → forget → no resurrection in Cases/Assistant surface
- [x] C37 Goose truthfulness covered in Brunch script (`possible_fix: NOT YET` unchanged)

## Test plan

- `pnpm exec vitest run src/pilot/BrunchProduct.test.tsx`
- `pnpm exec vitest run src/pilot/MondayMayaProduct.test.tsx`
- `pnpm exec vitest run src/pilot/HonkHonkProduct.test.tsx`
- `pnpm exec vitest run src/pilot/VerificationFailureProduct.test.tsx`
- `pnpm exec vitest run src/pilot/ForgetProduct.test.tsx`
- `uv run pytest apps/api/tests/test_p02_brunch_product.py apps/api/tests/test_p02_remaining_product.py`
- P01 freeze: `WorldIsolation.test.tsx` still passes
