# C38 — Shared uncertainty collapse (one investigation, many dependents)

**Status:** future  
**Branch:** `ticket/C38-shared-uncertainty-collapse`  
**Domain:** conversational-ui  
**Package boundary (docs capture):** `docs/architecture/cortex-visualizer.md` (shared-investigation rule — landed via [#104](https://github.com/oscarhilton/enigma-assistant-/pull/104) when merged), `docs/architecture/conversational-stream.md`, `tickets/conversational-ui/**`, cross-links in `docs/architecture/conversational-ui.md`  
**Package boundary (implementation — do not start):** `packages/domain/src/personal_enigma/domain/**` (epistemic dependency identity), `apps/api/src/personal_enigma/api/routes/demo.py` and event-spine modules (shared investigation + `dependency_resolved` propagation), `apps/api/src/personal_enigma/api/demo_orchestrator.py`, `apps/web/src/enigma/cortex/events.ts`, `apps/web/src/enigma/cortex/mapEvents.ts`, `apps/api/tests/test_c38_*.py`

**Hard depends:** [C28](./C28-event-spine-agent-work.md) Event Spine substrate (`work.*`, `world.dependency_arrived`, agent-work lifecycle) landed  
**Soft (~):** [C26](./C26-grounded-assertions-epistemics.md) · [C31](./C31-goose-work-projection-and-proactivity.md) · PILOT-01 (pilot behaviour exposes duplicate-investigation waste) · [#104](https://github.com/oscarhilton/enigma-assistant-/pull/104) shared-investigation doc freeze

**Unlocks / enhances:** One real Goose investigation waking multiple dependent concerns; Cortex forensic view of collapse instead of parallel comedy errands — **after** unpark only.

## Parked

```text
C28 Event Spine  →  PILOT-01 exposes waste  →  unpark C38 implementation
```

Do **not** implement now. Documentation capture below is the whole current scope.

## Frozen spec

> **Resolve shared uncertainty once, then propagate the result to every dependent concern.**
>
> **Do not duplicate investigation merely because the same uncertainty appears in multiple pieces of work.**

Principles frozen in [cortex-visualizer.md](../../docs/architecture/cortex-visualizer.md) ([#104](https://github.com/oscarhilton/enigma-assistant-/pull/104)):

1. **Identity is the uncertainty itself**, not vaguely similar tasks.
2. When birthday planning, weekend availability, and Sunday attention all depend on *“Do I work Monday?”*, Enigma runs **one** investigation, grounds **one** resolution, and propagates that result to dependents A / B / C.
3. **THE Goose:** one piece of real work with three dependents — not three comedy errands.
4. Event Spine already has most of the grammar (`work.created`, `work.investigating`, `work.waiting_external`, `world.dependency_arrived`, `dependency_key`).
5. **Squeeze only** when real pilot behaviour makes failing to recognise shared uncertainty visibly wasteful.
6. **Hard problem (leave open):** when are two questions the same epistemic dependency? Do not pretend this is solved in the ticket.

## Non-goals (must not)

- **No** `DependencyReasoningOrchestrator` or new top-level service
- **No** premature merging of vaguely similar tasks (“both mention brunch” ≠ same uncertainty)
- **No** epistemic backchannel — dependents inherit grounded resolution + evidence basis, not another agent’s deliberation prose ([C39](./C39-handoff-working-conclusion.md))
- **No** palace / omniscient Goose — collapse is observable work, not hidden coordination theatre
- **No** implementation under PILOT-01 / P02 live programme without unparking this ticket

## Acceptance criteria (implementation — after unpark)

Tests TBD when pilot exposes duplicate-investigation failure modes. Directional criteria:

- [ ] Two or more agent-work items blocked on the same epistemic uncertainty share one investigation identity (not task-title similarity)
- [ ] First investigation emits a single grounded resolution; dependents resume via propagated `dependency_resolved` (or equivalent spine event) with semantic result + evidence basis — not re-query from scratch
- [ ] Cortex / activity projection can show one investigation fan-out to N dependents (forensic, read-only)
- [ ] Distinct uncertainties with similar surface wording remain **separate** investigations (negative test)
- [ ] Idempotency: duplicate resolution events do not double-apply or fork state
- [ ] No new orchestrator service; logic stays inside existing Event Spine + domain epistemic models

## Test plan (after unpark)

- Fixture: three `work.*` items blocked on `uncertainty:monday-work-schedule` → one `work.investigating` → one resolution → three dependents reach `READY_FOR_USER` / continue without second calendar fetch
- Negative: “brunch Sunday?” and “book restaurant?” share wording but different dependency keys → two investigations
- Idempotency: replay `world.dependency_arrived` / resolution → no duplicate world writes
- Goose projection ([C31](./C31-goose-work-projection-and-proactivity.md)): UI shows one walk, three wakeups

## Privacy constraints

- Shared resolution must cite evidence handles ([C25](./C25-evidence-coverage-bundle.md) / [C26](./C26-grounded-assertions-epistemics.md)); no promotion of deliberation text to durable truth
- Remote inference sees compiled resolution summaries only through existing egress gate ([SEC-02](../security/SEC-02-audited-remote-egress-gate.md))

## Related

- [C28 — Event spine and agent-work lifecycle](./C28-event-spine-agent-work.md)
- [C39 — Handoff working conclusion](./C39-handoff-working-conclusion.md) (`dependency_resolved` semantic result shape)
- [cortex-visualizer.md](../../docs/architecture/cortex-visualizer.md) · [#104](https://github.com/oscarhilton/enigma-assistant-/pull/104)
- [ADR-029 — Context compilation](../../docs/adr/029-context-compilation-request-shaped-memory.md)
