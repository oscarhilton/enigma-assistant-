# Reasoning Value Gate — Live Fireworks lane

**Status:** Manual operator path (budget-capped)  
**Ticket:** [R-L03](../../tickets/reasoning/R-L03-fireworks-budget.md)  
**Replay CI:** unchanged — `enigma-eval --reasoning-gate` stays offline

## Purpose

Run the Reasoning Value Gate benchmark against **Fireworks GPT-OSS-120B** on fictional Alex checkpoints only, with a **$0.80 hard budget cap** and a local audit trail. CI never opens a network connection; live runs require explicit operator setup.

---

## Security checklist (before any spend)

| Check | Requirement |
| --- | --- |
| Data | **Alex synthetic only** — frozen evaluation snapshots / TransformedContext |
| Default path | Production privacy transform (`TransformedContext`); raw synthetic only in controlled ablation arms |
| API key | `FIREWORKS_API_KEY` from env or Keychain — **never commit** |
| Fireworks account | **Auto Reload OFF** — manual top-up only |
| Transport | Chat Completions only (`/chat/completions`) — no Responses API, no `store=True` |
| Audit | Local JSONL under `reports/reasoning-gate-live/` — usage + cost, **no API key** |
| Budget | Hard cap **$0.80** — refuse when `cumulative + projected_next_call > cap` |

---

## Environment

```bash
export FIREWORKS_API_KEY="..."   # never commit
# optional override:
export FIREWORKS_MODEL="accounts/fireworks/models/gpt-oss-120b"
```

Pricing constants (GPT-OSS-120B serverless) live in `benchmark_budget.py`:

- Input: **$0.15 / 1M tokens**
- Output: **$0.60 / 1M tokens**
- Hard cap: **$0.80**

---

## Components

| Module | Role |
| --- | --- |
| `packages/reasoning/.../fireworks_transport.py` | OpenAI-compatible Chat Completions to `https://api.fireworks.ai/inference/v1` |
| `packages/evaluation/.../benchmark_budget.py` | Budget ledger, pessimistic pre-call refusal, JSONL audit |

Deterministic **seed** per checkpoint + rep (`fireworks_seed`) keeps live reps reproducible.

---

## Operator runbook

```bash
git checkout main && uv sync

# Replay-only CI path (no key, no network):
uv run pytest packages/reasoning/tests/test_fireworks_transport.py
uv run pytest packages/evaluation/tests/test_benchmark_budget.py
uv run enigma-eval --reasoning-gate   # existing offline harness

# Live lane (after R-L04+ CLI lands — manual orchestration until then):
export FIREWORKS_API_KEY=...
# Smoke ($0.05 cap) → main A/B → disagreements → ablation → report
# See parent sprint plan in docs/demo/reasoning-value-gate.md
```

Audit log default path:

```
reports/reasoning-gate-live/budget-audit.jsonl
```

Each line records: `prompt_tokens`, `completion_tokens`, `estimated_cost_usd`, `cumulative_total_usd`, `checkpoint_id`, `rep`, `phase`, `model` (no secrets).

---

## Budget refusal rule

Before every live call the ledger computes a **pessimistic** projection:

```
projected = input_tokens × $0.15/M + max_output_tokens × $0.60/M
```

Refuse (raise `BudgetCapExceededError`) when:

```
cumulative_usd + projected > HARD_CAP_USD ($0.80)
```

After a successful call, record actual usage and append to the audit JSONL.

---

## Related docs

- [reasoning-value-gate.md](./reasoning-value-gate.md) — sprint charter (R01–R07)
- [ADR-012](../adr/012-reasoning-value-gate-decision.md) — architecture decision (live evidence fills this)
