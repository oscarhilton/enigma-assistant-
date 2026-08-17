# ADR-012: Reasoning Value Gate architecture decision

**Status:** Accepted (evidence from harness)
**Date:** 2026-08-17
**Git:** `f635380`

## Evidence

| Metric | Arm A | Arm B |
| --- | --- | --- |
| Critical recall | 0.500 | 0.500 |
| Top-3 critical recall | 0.500 | 0.500 |
| Next-action fit | 1.000 | 1.000 |
| Privacy ablation Δ | — | +0.000 |

## Decision

**keep_deterministic** — Heuristic matches or beats LLM (mean Δ=0.000).

See [reasoning-value-gate-report.md](../reports/reasoning-value-gate-report.md).
