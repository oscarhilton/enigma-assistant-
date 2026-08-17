# ADR-012: Reasoning Value Gate architecture decision

**Status:** Accepted (Arm B2 hypothesis — interim evidence; final gate pending R-L05 main A/B)
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

**Conclusion:** gpt-oss-120b did not reliably calibrate surface/suppress under judge-v1 direct-decision framing. The anchored path leaked evaluator labels into runtime context; the de-anchored path failed Brunch entirely. Model-direct interruption authority is the wrong abstraction.

Evaluator labels (`MUST_SURFACE`, `MUST_SUPPRESS`, `MUST_STAY_QUIET`) in `support_contracts.yaml` are **evaluator-only** — never injected into runtime prompts or policy.

## Arm B2 hypothesis (semantic judge + deterministic policy)

**Split responsibility:**

1. **Remote LLM** — semantic interpretation only (`semantic-judge-v1`): obligation strength, user responsibility, importance, time sensitivity, actionability, confidence, reason codes, optional next action.
2. **Local Enigma policy** — `packages/attention/interruption_policy.py` combines semantic features with observable facts (`now`, `due_at`, open/completion, calendar proximity, noise evidence patterns, restful-weekend mode) → `surface` / `context` / `suppress`.

Metrics score **`policy_judgement`** (post-policy alerts), not raw model output.

## Interim evidence (2026-08-17 — not final ADR decision)

| Track | Result |
| --- | --- |
| B1 direct judge | **FAILED** — de-anchored: Brunch 0/3; anchored path had evaluation leak |
| B2 semantic judge + policy | Live smoke **9/9** (Brunch / PrizeVault / Quiet — 3 cases × 3 reps) |
| Architecture boundary | LLM understands situation; **policy decides interruption** |

**Final ADR decision deferred** until R-L05 main A/B (20 checkpoints). Do **not** declare `clear_win` / `no_win` from smoke alone.

## Mock honesty

`SmokeOracleTransport` (formerly `SmokeMockTransport`) is plumbing-only: validates schema, policy wiring, and orchestration — **not** live prompt semantics. Regression path: record replay fixtures from real Fireworks responses via `ReplayPaygTransport`.

## Decision (pending main A/B)

Run live gate with `--arm b2` (default). B1 remains available for comparison (`--arm b1`). Do not spend budget on B1 prompt tuning.

## Related

- [reasoning-value-gate-live.md](../demo/reasoning-value-gate-live.md)
- `packages/reasoning/.../structured_output.py` — `SemanticJudgeV1Output`
- `packages/attention/.../interruption_policy.py` — deterministic policy
