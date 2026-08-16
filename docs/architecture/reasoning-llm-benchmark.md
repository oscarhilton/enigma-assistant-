# Controlled reasoning-LLM benchmark

**Status:** Design + scaffold (Arm B Judge harness stub).  
**Prerequisite:** Phase 2.5 used Provider: stub / remote calls 0.  
**ADR:** [ADR-011](../adr/011-llm-structured-judgement.md) — LLM proposes structured judgement; code decides; never raw `PrivatePerson` to a hosted model.  
**Related:** [attention-surface.md](./attention-surface.md) · [PaygReasoningService](../../tickets/reasoning/M05-payg-reasoning-provider.md) · D11 replay

Before expanding Shadow, we need a **controlled** comparison of how a reasoning
LLM judges open loops versus today’s deterministic attention path — on fictional
Alex only, with offline CI, and with code retaining final authority.

## Arms A–E

| Arm | Name | What changes | Why / when |
| --- | --- | --- | --- |
| **A** | Current | Deterministic attention + next-action path; Provider stub / remote calls 0 | Baseline. Same checkpoints and metrics as today. |
| **B** | LLM Judge | Local filter produces candidate open loops + evidence; hosted model emits **structured judgement only**; code applies policy | **First LLM arm** — fewest variables: candidates fixed, schema fixed, authority fixed. |
| **C** | LLM Discovery | Model may propose additional candidates / merges from a larger sanitised window | More degrees of freedom; run after Judge recall/precision are understood. |
| **D** | Hybrid | Local ranking + Judge on contested band (e.g. mid-confidence open loops only) | Cost/latency trade-off once B and C baselines exist. |
| **E** | Synthetic Oracle | Privileged access to scenario ground-truth labels at eval time (never at runtime) | Upper bound / calibration; not a product path. |

### Why Judge first (Arm B)

Arm B holds the candidate set, evidence IDs, checkpoint clock, and scoring rubrics
constant. The only new variable is “can a structured LLM judgement improve ranking /
suppression under code authority?” Arms C–E add discovery, routing, or oracle
leakage and would confound that answer.

## Structured judgement schema (no CoT)

The model must return JSON matching this shape (one object per candidate, or a
list under `judgements`). **No chain-of-thought, no free-form essay, no private
identifiers.**

| Field | Type | Notes |
| --- | --- | --- |
| `candidate_id` | string | Must match a frozen candidate in the request |
| `kind` | enum | e.g. `obligation` · `pending_reply` · `situational` · `noise` |
| `status` | enum | e.g. `open` · `resolved` · `stale` · `unknown` |
| `importance` | enum | `critical` · `high` · `medium` · `low` · `none` |
| `attention` | enum | `must_surface` · `may_surface` · `suppress` |
| `timing` | enum | `now` · `soon` · `later` · `too_late` · `n/a` |
| `confidence` | float | `[0, 1]` |
| `reason_codes` | string[] | Short machine codes only (e.g. `multi_source`, `deadline_72h`) — not prose |
| `evidence_ids` | string[] | Subset of IDs present in the request payload |

Rejected: narrative `rationale`, tool calls, raw emails, `PrivatePerson` fields,
or inventing evidence IDs.

## Code retains final authority

After the model responds, deterministic code **must**:

1. **Schema** — Pydantic validation; drop / fail closed on unknown fields that
   change meaning; refuse CoT blobs.
2. **Privacy** — Re-run remote-safety checks; zero privacy violations allowed.
3. **Evidence** — Every `evidence_id` must exist on the frozen candidate payload.
4. **Deadline** — Timing / importance inconsistent with injected clock + due_at
   may be clamped or rejected (policy-configurable).
5. **Budget** — Token / cost / latency ceilings; over-budget → fail that arm run.
6. **Policy** — MUST_SURFACE / MUST_SUPPRESS and product rules win over model
   `attention` when they conflict.

**LLM proposes; code decides.** Surfaced attention and next action are always
policy outputs, never raw model text.

## Whole-checkpoint evaluation

Evaluate at fixed scenario clocks (example: **Wed 21 Jan noon**), not per-event
streaming. At each checkpoint:

1. Freeze top-N candidates + evidence from Arm A (or a shared local filter).
2. Run the arm under test (A stub, B Judge, …).
3. Compare top-N surfaced items to **scenario truth** (obligations /
   attention windows / MUST_SURFACE · MUST_SUPPRESS labels).

Ideal first case: **parents / brunch** (Elena’s parents Saturday brunch) —
multi-source, concrete deadline, clear suppressible calendar noise. See
[attention-surface.md](./attention-surface.md). Catalogue expansion that adds
richer MUST_SURFACE / MUST_SUPPRESS labels is a **soft dependency**
([F-judgement-scenario-catalogue](../../tickets/demo-scenario/F-judgement-scenario-catalogue.md));
do not fight sibling `obligations.yaml` edits — reference their catalogue or
leave TODO pointers.

## Metrics

| Metric | Meaning |
| --- | --- |
| MUST_SURFACE recall | Fraction of labelled must-surface items in top-N |
| MUST_SUPPRESS violation | Labelled suppress items that still surface |
| Top-1 / Top-3 critical recall | Critical obligations in rank 1 / ≤3 |
| Displacement | How far truth items fall vs baseline rank |
| Timing | Early / on-time / late vs due window |
| False alerts | Surfaced items with no truth support |
| Silent misses | Truth must-surface absent from top-N |
| Next-action quality | Stub/rubric score vs authored next action |
| Tokens / cost / latency | Per checkpoint and per 1k signals |
| Privacy violations | **Must be 0** |
| Schema failures | Invalid / CoT / invented evidence |
| Run-to-run variance | Same fixture, **5 runs** (live or temperature>0); replay should be 0 |

## Privacy ablation (fictional Alex only)

Two payloads for the **same** synthetic candidates:

| Variant | Payload |
| --- | --- |
| Transformed | PERSON_* / sanitised summaries (`may_transmit_remotely=True`) |
| Raw synthetic private | Untransformed private-shaped text **from Demo fixtures only** |

Measure Judge quality delta **and** prove the production path never uses the raw
arm. Never run ablation on Private Mode user data. Ticket:
[F-llm-judge-privacy-ablation](../../tickets/demo-evaluation/F-llm-judge-privacy-ablation.md).

## Suspected eventual architecture

```text
local filter
    → 20–50 open loops (+ evidence)
    → LLM structured assess (Judge schema)
    → deterministic policy (authority)
    → attention surface + next action
```

This benchmark measures whether the middle step earns its cost before we wire it
into product paths. Shadow Mode remains gated on Phase 2.5 + F-* discipline
([shadow-mode-questions.md](./shadow-mode-questions.md)).

## Scaffold vs live keys

| Mode | CI | Developer |
| --- | --- | --- |
| DRY_RUN | Default — privacy gate + empty/structured stub, no network | OK |
| Fixture replay | Default for Arm B tests — frozen Judge JSON | OK |
| ENABLED live | **Not** in PR CI | Optional: `ENIGMA_LLM_JUDGE_LIVE=1` + API key |

Harness lives under `packages/evaluation` (`llm_judge/`), reusing
`PaygReasoningService` transport modes where a live call is opted in.

## Ticket map

| Ticket | Role |
| --- | --- |
| [F-llm-judge-harness](../../tickets/demo-evaluation/F-llm-judge-harness.md) | Arm B schema + authority + DRY_RUN / replay stub (**this scaffold**) |
| [F-judgement-scenario-catalogue](../../tickets/demo-scenario/F-judgement-scenario-catalogue.md) | Soft-dep: expand MUST_SURFACE / MUST_SUPPRESS / checkpoint truths (sibling) |
| [F-llm-judge-record-replay](../../tickets/demo-evaluation/F-llm-judge-record-replay.md) | Record live Judge pairs → CI fixtures (extends D11) |
| [F-llm-judge-privacy-ablation](../../tickets/demo-evaluation/F-llm-judge-privacy-ablation.md) | Raw vs PERSON_* ablation on Alex |
| [F-llm-arms-c-e](../../tickets/demo-evaluation/F-llm-arms-c-e.md) | Arms C–E later |
