# D08f-06 — June ordinary events (SEC-06/07 payoff substrate)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D08f-06-june` |
| Domain | `demo-scenario` |
| Parent | [D08f](./D08f-alex-six-month.md) |

## Package boundary (hard)

- May edit: `scenarios/alex-v1/timeline/2026-06/**`, `scenarios/alex-v1/content/**` (new bodies only), `scenarios/alex-v1/README.md` (span through 2026-06-30)
- Must not edit: other months’ committed events, `packages/ingestion/**`, C11 runtime, **SEC-07 attacker / scorer**, `intent_router.py`, Life Scripts

## Hard depends

- [D08f](./D08f-alex-six-month.md) programme

## Soft depends (~)

- [D08f-02](./D08f-02-february.md) loader. Do not block start.
- [SEC-06](../security/SEC-06-retention-memory-decay-forget.md) decay already landed
- [SEC-07](../security/SEC-07-shadow-reconstruction-benchmark.md) consumes this month — does not start here

## Shape (ordinary)

Keep June boring. The payoff is **time depth**, not a finale. Include enough still-active commitments that Enigma can be useful on 30 June, plus enough aged January detail that decay should have eaten narrative. One inspectable “what do you remember?” moment is a **Life Script** ([D08f-scripts](./D08f-scripts.md)), not a timeline essay.

## Non-goals

- Implementing the SEC-07 steal/reconstruct runner
- Compiling what Enigma *should* remember into a biography
- C11 implementation

## Acceptance criteria

- [ ] Source events only under `timeline/2026-06/` through ~2026-06-30
- [ ] At least one still-open ordinary loop on 30 June (mail/reminder/calendar — not a novel)
- [ ] No dump of six-month recap; no `ALEX_BIOGRAPHY.md`
- [ ] README notes June 30 as the intended SEC-07 snapshot instant
- [ ] No world-model keys

## Test plan

- After glob: June events load; max `at` on or before 2026-06-30
- Deterministic replay fingerprint includes June

## Privacy constraints

- Fictional only. Canaries remain the opt-in security overlay, not June plot.
