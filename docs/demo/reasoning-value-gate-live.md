# Reasoning Value Gate — Live Fireworks runbook

Manual, budget-capped live lane on fictional Alex only. CI stays replay-only.

## Prerequisites

- `FIREWORKS_API_KEY` in environment (never commit)
- Auto Reload **off** on Fireworks account
- Alex synthetic / Demo Mode only — no Shadow or Private data

## Operator sequence

```bash
export FIREWORKS_API_KEY=...   # Keychain / env
git checkout main && uv sync

# 1. Smoke ($0.05 cap, 3 cases × 3 reps — must be unanimous)
uv run enigma-eval --reasoning-gate-live --smoke-only --live

# 2. Main A/B ($0.25 target, 20 checkpoints × 3 reps)
uv run enigma-eval --reasoning-gate-live --phase main --live

# 3. Disagreements (5× reps on A≠B)
uv run enigma-eval --reasoning-gate-live --phase disagreements --live

# 4. Privacy ablation (10 hardest)
uv run enigma-eval --reasoning-gate-live --phase ablation --live

# 5. Exit report + manual next-action export
uv run enigma-eval --reasoning-gate-live --phase report --live
```

## Mock / CI (no API key)

```bash
uv run enigma-eval --reasoning-gate-live --smoke-only
uv run pytest packages/evaluation/tests/test_live_gate.py
```

## Budget

- Hard cap: **$0.80** (`benchmark_budget.HARD_CAP_USD`)
- Refuses when `cumulative + projected_next_call > cap`
- Audit log: `reports/reasoning-gate-live/budget-audit.jsonl`

## Architecture decision (ADR-012)

| Outcome | Criteria |
| --- | --- |
| **clear_win** | recall Δ≥+5pp AND suppress Δ≥-1pp AND regressions=0 AND schema/privacy=100% |
| **small_win** | hybrid threshold (recall Δ≥+2pp, ≤1 regression) |
| **no_win** | keep deterministic |

See [reasoning-value-gate-live-report.md](../reports/reasoning-value-gate-live-report.md).
