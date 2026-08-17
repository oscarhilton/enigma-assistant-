# C19 — Multi-intent decompose and unsupported reporting

**Status:** todo  
**Branch:** `ticket/C19-multi-intent-decompose`  
**Domain:** conversational-ui  
**May edit:** `apps/api/src/personal_enigma/api/demo_orchestrator.py` (clause continue / unsupported report), `apps/api/src/personal_enigma/api/context_compilation.py` (candidate families for compound PRIVATE_WORLD requests only), `apps/api/src/personal_enigma/api/speech_acts.py` (no new English catalogues — compound QUESTION stays QUESTION), `apps/api/tests/test_c19_*.py`, `docs/architecture/conversational-ui.md` (pointer), `tickets/conversational-ui/**`

**Must not edit:** `intent_router.py` phrase families · `ConversationCapsule` · C15 bootstrap · `timer.*` / `email.send` as new product assists · C09c `_FOLLOW_UP` · treating tool 200 as full-request SATISFIED when clauses remain

**Hard depends:** [C09](./C09-llm-conversational-boundary.md) compiler ([ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md)) · [C09c](./C09c-conversation-capsule.md) SATISFIED vs PARTIAL (consume, do not reopen)  
**Soft (~):** [C20](./C20-capability-contract-on-wire.md) — honest “I cannot email” needs the capability contract · [C18](./C18-active-thread-record.md) unresolved slots

## Goal

**Before more assists.** A compound request must not collapse to the first convenient tool.

Forensic dump: [`packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt`](../../packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt) ([C23](./C23-continuity-integrity-life-script.md)).

Turn 38 exact line: `we already picked right? is it in the calendar? can we make the email?`

Dump executed only `agenda.get` and answered “Needs you today: Book Saturday brunch… Strong next action: Draft colour + spacing token inventory. I don't see anything on the calendar today.” Venue and email clauses were dropped.

C09c explicitly left `support.decompose` out of the capsule ticket. This is that later product contract — orchestrator decomposition, not a capsule rebuild.

## Frozen rules

1. Decompose into clauses. Execute each **supported** intent (fresh tools this turn). Report each **unsupported** clause explicitly.
2. Partial tool success is PARTIAL request satisfaction ([ADR-030](../../docs/adr/030-conversation-capsule.md)). Do not mark SATISFIED because `agenda.get` returned 200.
3. Unsupported ≠ invent a send. Missing `email.send` is reported, not faked ([C20](./C20-capability-contract-on-wire.md), [C17](./C17-execution-receipts-verification-ledger.md)).
4. No new `intent_router` phrase families. No `_FOLLOW_UP` regex for “and also email them.”

## Deliverables

- [ ] Orchestrator continues until each supported clause has a tool result or an explicit unsupported marker
- [ ] Respond copy covers all clauses of dump turn 38 (`venue_selected` / `calendar` / `email`) — tests assert clause coverage, not exact prose
- [ ] Unsupported parts named; no silent drop
- [ ] Capsule assessment stays PARTIAL while any clause is unanswered

## Out of scope

Adding messaging / calendar-write assists so the email clause becomes true; capability-contract wire shape ([C20](./C20-capability-contract-on-wire.md) owns that); C09c; C15; timers. A **decomposition worker** is a later shape ([ADR-033](../../docs/adr/033-bounded-subtask-workers.md)); this ticket lands clause coverage in the parent orchestrator first.

## Definition of done

A three-clause private request executes every supported family and states the unsupported remainder. Dump turn 38 collapsing to `agenda.get` only is a failed test. Gate: [C23](./C23-continuity-integrity-life-script.md).
