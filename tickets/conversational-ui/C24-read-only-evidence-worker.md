# C24 — Read-only evidence worker (`"ffs"` path)

**Status:** future  
**Branch:** `ticket/C24-read-only-evidence-worker`  
**Domain:** conversational-ui  
**May edit (when unparked):** `apps/api/src/personal_enigma/api/subtask_workers.py` (new), `apps/api/src/personal_enigma/api/demo_orchestrator.py` (dispatch hook only — parent still speaks), `apps/api/tests/test_c24_*.py`, `packages/evaluation/scripts/alex_jan19_conversation_capsule.script.yaml` (assert fresh tool, not transcript ranking — do not rewrite the capsule episode), `docs/adr/033-*.md`, `docs/architecture/conversational-ui.md` (pointer), `tickets/conversational-ui/**`

**Must not edit:** `ConversationCapsule` / ADR-030 loop · `intent_router.py` · C15 bootstrap merge as an authority grant · worker-owned `current_subject_id` · worker prose to the user · `email.send` / `timer.*` · C16/C17 ledger files (P0 stays in those tickets)

**Hard depends:** [C09c](./C09c-conversation-capsule.md) landed · frozen · [C16](./C16-attested-completion-invalidates-next-action.md) `done` · [C17](./C17-execution-receipts-verification-ledger.md) `done`  
**Soft (~):** [C15](./C15-semantic-bootstrap-capsule.md) (consume interpretation; do not bypass the compiler) · [C21](./C21-grounded-values-no-invented-facts.md) · [C23](./C23-continuity-integrity-life-script.md) (this ticket does **not** block the 61-turn gate)

**Architecture:** [ADR-033](../../docs/adr/033-bounded-subtask-workers.md) · [ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md) · [ADR-030](../../docs/adr/030-conversation-capsule.md)

## Goal

**After P0, not instead of it.** First bounded worker: a read-only evidence hand behind the single speaking orchestrator.

`"ffs"` becomes: recover the unresolved request (capsule) → compile private READ (ADR-029) → dispatch a scoped evidence envelope → receive **fresh** evidence ids/claims, not transcript residue → parent answers.

Dump turn 20 exact line: `ffs` ([C23](./C23-continuity-integrity-life-script.md) intervening repair; this ticket does **not** block that gate).

This is OpenClaw-like delegation with Enigma’s control philosophy: the worker does not own the thread, referents, authority, satisfaction, or the final sentence.

## Frozen rules

1. Consume C09c `public_view()` and the compiled turn. Do **not** bypass the capsule or the compiler. Do **not** amend the capsule object.
2. Envelope authority is `READ` or `NONE` only. No `PROPOSE` on this first worker. Never `APPROVE` / `EXECUTE`.
3. Return `SubtaskResult` (claims, evidence ids, unresolved). No user-facing prose from the worker.
4. Parent satisfaction tracking and respond phase stay in the orchestrator. Worker `status` ≠ capsule SATISFIED ≠ execution receipt.
5. No second personality. No “evidence assistant” in the UI.
6. Do not claim this ticket until C16 and C17 are `done`.

## Deliverables (when unparked)

- [ ] `SubtaskEnvelope` / `SubtaskResult` types as [ADR-033](../../docs/adr/033-bounded-subtask-workers.md)
- [ ] Read-only evidence worker: allowed tools ⊆ compiled READ surface; output grounded claims + evidence ids
- [ ] `"ffs"` / mail-recency follow-up: parent dispatches worker after compile; answer requires this-turn evidence, not `recent_dialogue` ranking
- [ ] Tests: worker cannot call `assist.propose` / `assist.approve`; worker cannot emit “I sent it”; compiler-denied tools are absent from `allowedTools`

## Out of scope

P0 attestation / receipts ([C16](./C16-attested-completion-invalidates-next-action.md), [C17](./C17-execution-receipts-verification-ledger.md)); decomposition worker (later shape of [C19](./C19-multi-intent-decompose.md)); explanation worker; action-verification worker (later shape of C17); external-world researcher; C09c mechanism; more assists; C11 / C22 personalities.

## Definition of done

The `"ffs"` path still inherits the live frame, still re-earns READ, and answers from a worker result that cites fresh private evidence. The parent still speaks. P0 tickets are already `done`.
