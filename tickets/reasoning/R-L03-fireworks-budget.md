# R-L03 — Fireworks transport + budget ledger

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/R-L03-fireworks-budget` |
| Domain | `reasoning` + `evaluation` |

## Package boundary (hard)

- May create/edit: `packages/reasoning/**`, `packages/evaluation/src/personal_enigma/evaluation/benchmark_budget.py`, `packages/evaluation/tests/test_benchmark_budget.py`
- May edit: `docs/demo/reasoning-value-gate-live.md`
- Must not edit: apple-bridge, ingestion sources, live orchestrator (R-L04+)

## Hard depends

- R-L02 judge-v1 schema (~ — soft if replay schema unchanged)

## Unlocks

- R-L04 smoke gate, R-L05 live A/B orchestrator

## Acceptance criteria

- [x] `FireworksChatTransport` — OpenAI-compatible Chat Completions to Fireworks
- [x] Base URL `https://api.fireworks.ai/inference/v1`; default model `accounts/fireworks/models/gpt-oss-120b`
- [x] Chat Completions only — no Responses API, no `store=True`
- [x] Deterministic `seed` per checkpoint + rep
- [x] `FIREWORKS_API_KEY` env (never committed)
- [x] `benchmark_budget.py` with `HARD_CAP_USD=0.80`, pricing constants
- [x] Refuse when `cumulative + projected_next > HARD_CAP` (pessimistic max output)
- [x] Per-request log: prompt_tokens, completion_tokens, estimated_cost, cumulative_total
- [x] Local JSONL audit under `reports/reasoning-gate-live/`
- [x] Security checklist + runbook in `docs/demo/reasoning-value-gate-live.md`

## Test plan

- [x] Budget projected-cost refusal at $0.79 + $0.08 call
- [x] Transport mock (no network in CI)
- [x] Audit log writes

## Privacy constraints

- Transport accepts `TransformedContext` only (same boundary as M19 OpenAI transport)
- Audit log never stores API keys
