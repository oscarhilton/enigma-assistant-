# Feature scenario — background-volume-vs-importance

| Field | Value |
| --- | --- |
| Status | `done` |
| Domain | `demo-scenario` |
| Related | D08c, D07, D08e |
| Branch | `ticket/f-quality-attacks` |
| Path | `scenarios/feature/background-volume-vs-importance/` |

## Intent

Large irrelevant thread (high message volume) versus a small critical canonical obligation. Attention must prefer the obligation, not frequency.

## Package boundary

- `scenarios/feature/background-volume-vs-importance/**`
- `packages/evaluation/tests/test_f_quality_attacks.py`

## Acceptance

- [x] High-volume background thread (≥30) does not outrank explicit canonical commitment
- [x] HeuristicAttentionEngine prefers EXPLICIT_REMINDER over high-score fluff inferences
- [x] Critical recall holds with volume present; payloads omit evaluator labels
