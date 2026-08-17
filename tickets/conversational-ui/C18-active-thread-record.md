# C18 — Active thread record (sibling of the capsule)

**Status:** todo  
**Branch:** `ticket/C18-active-thread-record`  
**Domain:** conversational-ui  
**May edit:** `apps/api/src/personal_enigma/api/conversation_context.py` (`ActiveThread` dataclass + `ConversationContext.active_thread` only — **do not change `ConversationCapsule`**), `apps/api/src/personal_enigma/api/context_compilation.py` (compile `active_thread` as a sibling of capsule `public_view()`, not inside it), `apps/api/src/personal_enigma/api/demo_orchestrator.py` (update thread after tools / decisions), `apps/api/tests/test_c18_*.py`, `docs/architecture/conversational-ui.md` (thread section), `tickets/conversational-ui/**`

**Must not edit:** `ConversationCapsule` fields or reducer · ADR-030 loop · inherit-authority · `_FOLLOW_UP` phrases · `intent_router.py` · C15 bootstrap · new Assist kinds · putting receipts *inside* the capsule

**Hard depends:** [C09c](./C09c-conversation-capsule.md) landed · frozen (consume `public_view()`; do not extend the object)  
**Soft (~):** [C17](./C17-execution-receipts-verification-ledger.md) — thread may store `last_execution_receipt` as an **id pointer** into the ledger · [C09b](./C09b-discourse-focus.md) focus vs objects

**Architecture:** [ADR-030](../../docs/adr/030-conversation-capsule.md) (capsule stays the decaying frame) · [ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md) · [ADR-032](../../docs/adr/032-action-ledger-execution-receipts-verification.md)

## Goal

**Before more assists.** Compact, deterministic thread state so dump referents keep their obvious bindings.

Forensic dump: [`packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt`](../../packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt) ([C23](./C23-continuity-integrity-life-script.md)).

Exact lines:

- Turn 2: `what should I do with this free time?` (dump: generic hobby essay; subject was TOKEN)
- Turn 13: `what else is on?` (dump asked what “on” meant)
- Turn 18: `and?` (dump: “which topic or statement”)
- Turn 53: `where did you get the colours from` (dump: “I’m not sure which colors you’re referring to”)
- Turn 55: `Should I let someone know?` (dump: generic ethics table)
- Turn 57: `did you really let them know?` (dump: “I’m not sure who “them” refers to”)

C09c already carries typed `RequestKind` + decaying frame + `unresolved_request`. `current_subject_id` is present and too thin. This ticket **adds** decisions / commitments / receipt pointers / slots on `ConversationContext`. It does **not** rebuild the capsule.

## Shape (deterministic, not LLM memory)

```text
active_thread:
  task_id
  goal
  status
  known_facts[]
  decisions[]
  unresolved_slots[]
  last_assistant_commitment
  pending_action
  last_execution_receipt   # id into the C17 ledger, or null
```

World establishes truth. The thread is conversation working memory: what this thread has decided, promised, and still needs. Facts in `known_facts[]` must be ids or tool-backed summaries — not a biography, not a transcript.

## Frozen rules

1. Sibling of `capsule` on `ConversationContext`. Not a field of `ConversationCapsule`.
2. Evidence/constraints still inherit via the capsule. Authority is still re-earned. Do not inherit APPROVE/EXECUTE on the thread.
3. `last_assistant_commitment` is what Enigma said it would do — not proof it did it. Proof is the ledger ([C17](./C17-execution-receipts-verification-ledger.md)).
4. Unresolved slots decay or resolve; they are not `_FOLLOW_UP` regex.
5. Capsule still recovers the question, not the answer. Thread must not become world truth ([ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md)).

## Deliverables

- [ ] `ActiveThread` on `ConversationContext`; compiler may send a tiny non-authoritative thread view next to capsule `public_view()`
- [ ] Populate from structured tool results / user decisions this session — not from transcript invention
- [ ] Tests: dump turns 2 / 18 / 53 / 55 / 57 (`what should I do with this free time?` / `and?` / `where did you get the colours from` / `Should I let someone know?` / `did you really let them know?`) resolve against thread+capsule without new router phrases
- [ ] Capsule unit tests stay green; no new capsule fields

## Out of scope

Receipt minting ([C17](./C17-execution-receipts-verification-ledger.md)); next-action overlay ([C16](./C16-attested-completion-invalidates-next-action.md)); multi-intent ([C19](./C19-multi-intent-decompose.md)); C09c mechanism; C15 live bootstrap; more assists.

## Definition of done

Elliptical referents in the C18 tests bind to the live thread (goal, entities, decisions, slots) while the capsule loop remains untouched. `current_subject_id` alone is no longer the only continuity object. Gate: [C23](./C23-continuity-integrity-life-script.md).
