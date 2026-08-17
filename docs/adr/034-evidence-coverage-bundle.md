# ADR-034: Evidence coverage bundle — satchel semantics and courier / Goose presentation

**Status:** Accepted  
**Date:** 2026-08-17

> **Every read turn returns a typed satchel — not vibes.**
>
> **Empty-pawed ≠ permission to improvise.**
>
> **The courier carries evidence; Enigma speaks.**

## Context

The conversational UI can show *what Enigma checked*, but users still receive confident prose when only one cupboard was opened (`agenda.get` on an empty calendar) while attention, sources, and blockers were never queried. The 14-turn coverage dump (Jan 17 session) shows compiler mis-missions and planner under-fetch collapsing into “Nothing needs you today.”

[C14](../../tickets/conversational-ui/C14-conversation-activity-stream.md) projects tool hops. [C20](../../tickets/conversational-ui/C20-capability-contract-on-wire.md) names capability absences. [C21](../../tickets/conversational-ui/C21-grounded-values-no-invented-facts.md) blocks invention. None of these expose **coverage adequacy**: whether the turn searched enough sources to support the conclusion.

[C24](../../tickets/conversational-ui/C24-read-only-evidence-worker.md) / [ADR-033](./033-bounded-subtask-workers.md) forbid a second speaking personality. The **evidence courier** is not an assistant — it is a presentation projection of the bundle, like the activity strip with a coverage vocabulary. It may later be rendered as **THE Goose**, but that rendering must remain strictly downstream of real work/evidence state.

## Decision

### EvidenceBundle (wire object)

Each read turn attaches an `EvidenceBundle` to `llm_trace`:

| Field | Meaning |
| --- | --- |
| `mission` | Compiler `FetchMission` — planned cupboards for this question |
| `searched_sources` | Sources actually read this turn |
| `empty_sources` | Read tools that returned no evidence |
| `unsearched_sources` | On the mission map but never opened |
| `unavailable_sources` | Locked doors (`capability_contract` + question-implied externals) |
| `evidence` | Typed `EvidenceItem[]` (ids only on wire) |
| `unresolved_referents` | Named mentions that did not bind |
| `conflicts` | Contradictory scraps (future) |
| `coverage_adequate` | May Enigma conclude the human question is answered? |

`coverage_adequate == false` means **empty cupboard ≠ empty house**. Enigma must not claim “nothing needs you” or invent facts to fill silence.

### FetchMission

Deterministic compiler output derived from `request_kind`, capability families, scope, and temporal constraints — not model-chosen.

Example catch-up mission:

```python
{
  "question": "What have I missed at work?",
  "request_kind": "catch_up",
  "scope": "work",
  "authority": "READ",
  "planned_tools": [
    "attention.get_current",
    "world.get_changes",
    "world.get_blockers",
    "agenda.get",
  ],
}
```

### Courier / Goose projection

Product-facing states derived from the bundle:

| State | Condition |
| --- | --- |
| `fetching` | Real in-flight read hop (C14 SSE) |
| `returned` | Non-empty evidence |
| `empty_pawed` | Searched, all empty, coverage adequate |
| `partially_returned` | Unsearched or unavailable sources block the conclusion |
| `confused` | Unresolved referent |
| `blocked` | Required capability absent |

The courier never speaks independently. Enigma narrates; the projection is icon + coverage line in NORMAL mode.

If Product Language renders the courier as **THE Goose**, that layer is still bound by two hard rules:

- Core state drives Goose state. Goose state never drives core state.
- Goose presentation must not determine truth, tool choice, retries, work scheduling, escalation, interruption, or authority.

### C24 alignment

The read-only evidence worker ([C24](../../tickets/conversational-ui/C24-read-only-evidence-worker.md)) executes `FetchMission.planned_tools` and returns a bundle-shaped `SubtaskResult`. The parent orchestrator still speaks.

## Consequences

- [C25](../../tickets/conversational-ui/C25-evidence-coverage-bundle.md) owns bundle builder, compiler mission fixes, grounding consumption, and courier UI v0.
- ADR-033 “no evidence assistant in the UI” means **no second conversational voice** — courier projection is allowed.
- Assist execution (`assist.executing`) stays on Assist cards + C17 receipts — not the courier.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Pet as LLM persona | Recreates authority leakage ADR-020 forbids |
| Activity strip only | Shows hops, not coverage gaps |
| Model self-report of sources | Unauditable; must be derived from trace |
