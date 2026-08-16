# ADR-011: LLM proposes structured judgement; code decides

## Status

Accepted

## Context

Phase 2.5 Demo Mode proved the pipeline with Provider: stub / remote calls 0.
Before more Shadow work, we need a **controlled reasoning-LLM benchmark** that
can compare deterministic attention against hosted models — without enlarging
the remote model’s view of the user’s private world, and without letting free-form
model text become product behaviour.

`PaygReasoningService` already gates on `TransformedContext` with
DISABLED / DRY_RUN / ENABLED. A Judge arm needs a stricter contract: structured
fields only (no chain-of-thought), and an explicit authority boundary so schema,
privacy, evidence integrity, deadlines, budgets, and product policy stay in code.

## Decision

1. **LLM proposes; code decides.** A hosted Judge may emit only a structured
   judgement object (`kind`, `status`, `importance`, `attention`, `timing`,
   `confidence`, `reason_codes`, `evidence_ids`). It must not emit free-form
   plans, CoT, or private identifiers. Deterministic policy code retains final
   authority: schema validation, privacy gate, evidence-ID membership, deadline
   consistency, token/cost budget, and MUST_SURFACE / MUST_SUPPRESS policy.
2. **Transmit TransformedContext only.** Remote Judge calls accept sanitised
   candidate + evidence payloads built from `TransformedContext` / PERSON_*
   tokens. Never send raw `PrivatePerson`, wholesale Notes, or raw attendee
   emails to a hosted model ([product rule](../architecture/overview.md)).
3. **CI stays offline.** Default Judge harness modes are DRY_RUN and
   fixture-replay. Live ENABLED requires an explicit developer env flag **and**
   an API key; PR CI must never depend on network or live keys.
4. **Judge first among benchmark arms.** Arms C–E (Discovery, Hybrid, Synthetic
   Oracle) are later tickets; Arm B (LLM Judge) isolates the fewest variables
   on top of Arm A (Current).

## Consequences

- Evaluation owns Judge schema + authority under `packages/evaluation`; PAYG
  transport remains the network boundary in `packages/reasoning`.
- Privacy ablation (raw synthetic private vs PERSON_* transform) is a separate
  measured experiment on fictional Alex only — never on Private Mode data.
- Product architecture may later become:
  local filter → 20–50 open loops → LLM structured assess → deterministic policy
  → attention + next action; this ADR does not ship that path, only the
  authority invariant required to measure it safely.
- See [reasoning-llm-benchmark.md](../architecture/reasoning-llm-benchmark.md).
