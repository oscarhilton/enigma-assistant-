# F — Eval noise metrics (corpus plan §38–48)

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/eval-noise-metrics` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/**`, `tickets/demo-evaluation/**`
- Must not edit: scenario corpora, demo UI, ingestion

## Hard depends

- D07, D08d, D08e

## Soft depends (~)

- D08c A/B artefacts

## Acceptance criteria

- [x] Background Suppression Rate in enigma-eval `metrics.json`
- [x] Background False Alerts / 1k in `suppression` (+ scale)
- [x] Attention Compression Ratio
- [x] Storyline Recall Under Noise (A/B) via `spine_metrics` / `--spine-metrics`
- [x] Remote reasoning rate stub (`remote_reasoning_rate_per_1k`)
- [x] Cost per simulated month stub (`cost_per_simulated_month`)
- [x] Mini-fixture tests

## Test plan

- [x] `tests/fixtures/noise_mini/` + `test_noise_metrics_report.py`
- [x] Schema snapshot includes suppression / cost / remote aliases

## Privacy constraints

- Reports Demo Mode only; no Private roots
