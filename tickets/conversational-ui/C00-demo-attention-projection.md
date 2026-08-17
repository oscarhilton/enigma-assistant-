# C00 — Demo attention projection backend

**Status:** in_progress  
**Branch:** `ticket/C00-demo-attention-projection`  
**May edit:** `apps/api/src/personal_enigma/api/routes/demo.py`, `apps/api/src/personal_enigma/api/demo_projection.py`, `packages/attention/src/personal_enigma/attention/projection.py`, `packages/attention/src/personal_enigma/attention/snapshot.py`, `packages/fixtures/**`, `packages/simulation` (checkpoint restore if needed)  
**Must not edit:** `apps/web`, transformation, reasoning weights

## Architectural guardrail (hard)

> `packages/evaluation` may be used to **establish parity during C00** (compare against frozen Step 7 / arm-a snapshots). It **must not** become a permanent runtime dependency of `apps/api`. Shared projection logic lives in `packages/attention`; Demo API reads checkpoints via `packages/fixtures`.

```
              shared Enigma projection (packages/attention)
                     ↑              ↑
                     │              │
                 Demo API       Evaluation
                     ↑
                 Simulation
```

Not: `Demo API → Evaluation`.

## Deliverables

- [x] Wire demo session to `SimulationClock` + checkpoint jump (`cp-2026-01-19T10:00`, `cp-2026-01-20T11:00`)
- [x] `GET /demo/attention/state` returns `AttentionState` with separate `needs_you`, `context`, `next_actions` (context ≠ worth doing)
- [x] `GET /demo/attention/{id}/qualification-debug` — composite breakdown (R-L10 formula)
- [x] `POST /demo/timeline/checkpoint/{id}` — jump to eval checkpoint instant
- [x] Demo event log records proactive silence; conversation unchanged

## Acceptance

Jan 19 10:00 and Jan 20 11:00 payloads match R-L10 decomposition semantics (token in **context** on Jan 20, brunch in **needs_you**).

**Hard depends:** D1  
**Unlocks:** C02, C03, C04, C05, C06
