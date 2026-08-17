# C22 — ADHD-hostile response shape (one / one / one)

**Status:** future  
**Branch:** `ticket/C22-adhd-response-shape`  
**Domain:** conversational-ui  
**May edit (when unparked):** `apps/api/src/personal_enigma/api/demo_orchestrator.py` (respond-phase default shape), `apps/api/tests/test_c22_*.py`, `docs/architecture/conversational-ui.md`, `docs/architecture/ethics.md` (pointer only), `tickets/conversational-ui/**`

**Must not edit:** `intent_router.py` · C09c · C15 · C11 tone store · a polish LLM · P0 ledger/next-action files

**Hard depends:** [C16](./C16-attested-completion-invalidates-next-action.md) · [C17](./C17-execution-receipts-verification-ledger.md) (P0 integrity first)  
**Soft (~):** [C09](./C09-llm-conversational-boundary.md) respond phase · [C11](./C11-tone-memory.md) (distinct — this is default *structure*, not style enums)

## Goal

Default replies are **one recommendation, one reason, one next action**. Generic essays, tables, redundant questions, and recaps are ADHD-hostile.

Forensic dump (soft examples, do not block P0): [`packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt`](../../packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt) ([C23](./C23-continuity-integrity-life-script.md)). Turns 2, 6, 14, and 55 answered `what should I do with this free time?` / `who do I ask for help` / `any other tasks?` / `Should I let someone know?` with tables and essays.

Do **not** claim this ticket. Do **not** block P0. Integrity of world and receipts first; then brevity.

## Frozen rules

1. Shape is a respond-phase default, not a second personality LLM ([ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md)).
2. Not [C11](./C11-tone-memory.md): tone memory is how to speak after C09 LLM proof. This ticket is information architecture of a turn.
3. Do not hide unsupported clauses ([C19](./C19-multi-intent-decompose.md)) in the name of brevity. One/one/one is the default; compound requests still cover every clause, shortly.
4. Fireworks is not solely at fault. Empty compiled context still produces chatbot sludge; fixing C16–C21 reduces the need for essays.

## Deliverables (when unparked)

- [ ] Default respond contract: one recommendation · one reason · one next action
- [ ] Tests: essay/table/recap `must_not` on a simple next-action turn
- [ ] Compound turns remain clause-complete without becoming a briefing pack

## Out of scope

P0 work; more assists; C09c; C15; claiming before C16+C17 `done`.

## Definition of done

Simple WORTH DOING turns no longer default to tables, recaps, or stacked questions. P0 tickets are already `done`.
