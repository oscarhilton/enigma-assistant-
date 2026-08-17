# Reasoning Value Gate Report

- Generated: 2026-08-17T07:24:35.319021+00:00
- Git: `f635380`
- Scenario: `alex-v1` v0.2.1

## Exit gate metrics

| Metric | Arm A (heuristic) | Arm B (LLM) | Ablation Δ |
| --- | --- | --- | --- |
| Critical recall | 0.500 | 0.500 | +0.000 |
| Must-suppress accuracy | 1.000 | 1.000 | +0.000 |
| Top-3 critical recall | 0.500 | 0.500 | +0.000 |
| Next-action fit | 1.000 | 1.000 | +0.000 |
| Median latency | 0.0 ms | 0.1 ms | — |
| Cost / simulated month | ~$0 | $0.0020 | — |

## Architecture decision

**Decision:** `keep_deterministic`

Heuristic matches or beats LLM (mean Δ=0.000).

## Failure attribution summary

- No A/B disagreements requiring attribution.
