# R-L05 — Main live A/B run

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/R-L04-L08-live-gate` |

## Acceptance criteria

- [x] `live_benchmark.py` — Arm A frozen, Arm B 3 reps × 20 checkpoints
- [x] Metrics: recall, suppress, top1/top3, stability, rescues/regressions
- [x] First-pass budget target <$0.25 (ledger enforced)
