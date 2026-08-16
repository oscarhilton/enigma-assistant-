# Product demo walkthrough

Operator guide for the curated Phase 2 Demo Mode path (`scenarios/product-demo`).

## Goal

Show that Enigma develops continuity: **day-one emptiness → weeks of evidence →
attention that reflects open loops**, without exposing ground truth in the UI.

## Prerequisites

- `ENIGMA_ENVIRONMENT_MODE=demo`
- Scenario: `product-demo` (or `alex-v1` for the full three-week corpus)
- Web Demo chrome (D10) and evaluation CLI (D07) available

## Operator steps

1. Open Demo Mode overview (`/demo`) — banner must read `DEMO MODE — FICTIONAL DATA ONLY`.
2. Confirm simulated clock starts at `2026-01-05` (day one: contact + standup only).
3. Advance day / step through week 1 until Q1 roadmap mail + reminder appear.
4. Continue through week 2 checkout recommendation (resolved).
5. Stop after week 3 Sam empty-state loop remains open.
6. Open **Attention** — expect the open Sam loop to surface (no ground-truth labels).
7. Open **Memory** / **Why** / **Privacy** hooks to show local continuity + privacy posture.
8. Optional eval snapshot:

```bash
uv run enigma-eval product-demo
# Compare narrative continuity vs MVP tag v0.1.0-mvp (6253f96) control:
# MVP had no multi-week demo corpus; Phase 2 proves continuity harness exists.
```

## Expected screens

| Step | Screen | Expect |
| --- | --- | --- |
| 1 | Demo overview | Persistent DEMO MODE banner; timeline controls |
| 2 | Day one | Sparse calendar/contact only |
| 3–5 | Timeline advance | Mail/reminders/notes accumulate |
| 6 | Attention | Open loop (Sam empty states) visible |
| 7 | Privacy | No Private credentials / real sources |

## Eval snapshot vs `v0.1.0-mvp`

| Control (`v0.1.0-mvp`) | Phase 2 product demo |
| --- | --- |
| No Demo environment separation | Demo/Private roots split (ADR-005) |
| No simulation clock | Injectable SimulationClock (ADR-006) |
| No scenario corpus | product-demo + alex-v1 benchmarks |
| No missed-obligation detector | D06/D07 ground truth + eval runner |
