# D02 — Simulation clock

| Field | Value |
| --- | --- |
| Status | `done` (merged #23) |
| Branch | `ticket/D02-simulation-clock` |
| Domain | `demo-environment` |
| Baseline | `v0.1.0-mvp` |

## Package boundary (hard)

- May edit: `packages/simulation/src/personal_enigma/simulation/clock.py`
- May edit: `packages/simulation/tests/test_clock.py` (create as needed)
- May edit: domain-time call sites in `packages/{attention,obligations,embeddings,transformation,identity,dedupe,privacy}/**` and `apps/{api,worker}/**` to accept injected `Clock`
- May add/amend: [ADR-006](../../docs/adr/006-clock-injection.md)
- Must not edit: scenario corpora, synthetic adapters (D04), eval metrics (D07)

## Hard depends

- D01

## Soft depends (~)

- None

## Unlocks / enhances

- Deterministic overdue / decay / recency in Demo
- Unlocks trustworthy D05 simulation and D07 evaluation

## Non-goals

- Replacing wall-clock in logging/telemetry
- Scenario timeline authoring (D03/D05)
- Filling Alex corpus (D08)

## Acceptance criteria

- [x] Shared `Clock` protocol with `now()` (timezone-aware)
- [x] `SystemClock` for Private; `SimulationClock` with `advance(...)` for Demo
- [x] Environment from D01 supplies the active clock
- [x] Domain decisions affecting deadlines, commitments, overdue, snooze, memory decay, event recency, attention escalation, retrieval recency, notification timing use `clock.now()` — not naked `datetime.now()` / `utcnow()` / `date.today()` / `time.time()`
- [x] Repo audit documents remaining wall-clock uses (logging OK; domain leaks fail CI or ticket checklist)

## Test plan

- Advance simulation clock → overdue / ranking inputs change without waiting on wall time
- Grep/audit test or script fails on new domain `datetime.now()` in owned packages (as agreed in PR)

## Privacy constraints

- Clock injection must not require shipping Private timestamps to remote models beyond existing transform rules
