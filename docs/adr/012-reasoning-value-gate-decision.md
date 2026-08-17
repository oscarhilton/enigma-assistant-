# ADR-012: Reasoning Value Gate — architecture decision

## Status

Proposed (stub — evidence filled by [R07](../../tickets/reasoning/R07-reasoning-value-gate-report.md))

## Context

Before investing in Tauri, Shadow features, 40k corpus generation, or runtime Next Action, Enigma must answer:

> **Does a reasoning LLM materially beat deterministic heuristics on attention and next-action decisions — on identical evidence, with trustworthy ground truth?**

The [Reasoning Value Gate sprint](../../docs/demo/reasoning-value-gate.md) runs Arm A (frozen heuristic baselines) vs Arm B (PaygReasoningService with structured JSON) across 15–25 alex-v1 checkpoints, scoring both **attention accuracy** and **support fitness**, with failure attribution and privacy ablation.

This ADR records the **architecture decision** once [R07](../../tickets/reasoning/R07-reasoning-value-gate-report.md) produces measured evidence — not hypothetical numbers.

## Decision

**Pending R07 report.** Select one outcome row below and fill the evidence column with measured metrics from the gate report.

| Outcome | Evidence (fill from R07) | Architecture path |
| --- | --- | --- |
| **LLM clearly wins** | _TBD — critical recall, suppress accuracy, next-action fit deltas_ | **Adopt:** local evidence → privacy transform → reasoning LLM → structured judgement → deterministic policy enforcement |
| **Barely wins** | _TBD — marginal deltas; attribution dominated by INTERPRETATION on low-confidence cases_ | **Hybrid:** obvious cases → local heuristics; uncertain checkpoints → LLM with structured output |
| **LLM loses** | _TBD — no material gain or regression on suppress accuracy / latency / cost_ | **Keep deterministic core;** defer LLM integration; invest in retrieval, memory, and ingestion quality |

## Consequences

- **If adopt:** Reasoning becomes a first-class stage after privacy transform ([M05](../../tickets/reasoning/M05-payg-reasoning-provider.md)); attention policy consumes structured LLM judgement, not raw chain-of-thought.
- **If hybrid:** Define confidence gate thresholds; LLM calls budgeted per checkpoint; replay transport remains CI path.
- **If keep deterministic:** LLM remains optional/disabled by default; sprint still delivers attribution map for where heuristics fail without LLM cost.

## Related

- [reasoning-value-gate.md](../demo/reasoning-value-gate.md) — sprint charter
- [ADR-011](./011-observable-support-challenges-only.md) — evaluator-only support challenges
- [executive-function-support-benchmark.md](../architecture/executive-function-support-benchmark.md) — dual checkpoint questions
- R01–R07 tickets under [tickets/reasoning/](../../tickets/reasoning/)
