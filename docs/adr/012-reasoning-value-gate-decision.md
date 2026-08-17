# ADR-012: Reasoning Value Gate architecture decision

**Status:** Accepted (Arm B2 hypothesis — live evidence pending)
**Date:** 2026-08-17

## Context

The Reasoning Value Gate compares frozen Arm A (deterministic heuristic) against Arm B (remote LLM on sanitised Alex checkpoints).

## Arm B1 result (direct judge-v1 surface/suppress)

Live smoke with **gpt-oss-120b** under judge-v1 direct-decision framing:

| Case | Before (leak) | After de-anchor prompt |
| --- | --- | --- |
| Brunch (must surface) | 3/3 | 0/3 |
| PrizeVault (must suppress) | 3/3 | 0/3 |
| Quiet weekend | 0/3 | 0/3 |

**Conclusion:** gpt-oss-120b did not reliably calibrate surface/suppress under judge-v1 direct-decision framing. The current experiment does not demonstrate reliable temporal attention calibration without policy anchoring. Model-direct interruption authority is the wrong abstraction.

Evaluator labels (`MUST_SURFACE`, `MUST_SUPPRESS`, `MUST_STAY_QUIET`) in `support_contracts.yaml` are **evaluator-only** — never injected into runtime prompts or policy.

## Arm B2 hypothesis (semantic judge + deterministic policy)

**Split responsibility:**

1. **Remote LLM** — semantic interpretation only (`semantic-judge-v1`): obligation strength, user responsibility, importance, time sensitivity, actionability, confidence, reason codes, optional next action.
2. **Local Enigma policy** — `packages/attention/interruption_policy.py` combines semantic features with observable facts (`now`, `due_at`, open/completion, calendar proximity, noise evidence patterns, restful-weekend mode) → `surface` / `context` / `suppress`.

Metrics score **`policy_judgement`** (post-policy alerts), not raw model output.

## Mock honesty

`SmokeOracleTransport` (formerly `SmokeMockTransport`) is plumbing-only: validates schema, policy wiring, and orchestration — **not** live prompt semantics. Regression path: record replay fixtures from real Fireworks responses via `ReplayPaygTransport`.

## Decision (pending live B2 smoke)

Run live gate with `--arm b2` (default). B1 remains available for comparison (`--arm b1`). Do not spend budget on B1 prompt tuning.

## Related

- [reasoning-value-gate-live.md](../demo/reasoning-value-gate-live.md)
- `packages/reasoning/.../structured_output.py` — `SemanticJudgeV1Output`
- `packages/attention/.../interruption_policy.py` — deterministic policy
