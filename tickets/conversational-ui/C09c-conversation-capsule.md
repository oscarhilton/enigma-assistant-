# C09c — Conversation capsule loop

**Status:** **landed** · **frozen** (do not reopen the capsule mechanism)  
**Branch:** `ticket/C09c-conversation-capsule` (implement in the C09 working tree; C09 owns `conversation_context.py`)  
**Domain:** conversational-ui  
**May edit:** `apps/api/src/personal_enigma/api/conversation_context.py`, `apps/api/src/personal_enigma/api/context_compilation.py`, `apps/api/src/personal_enigma/api/demo_orchestrator.py`, `apps/api/src/personal_enigma/api/demo_tools.py`, `apps/api/src/personal_enigma/api/semantic_bootstrap.py`, C09 tests, `packages/evaluation/scripts/alex_jan19_conversation_capsule.script.yaml`, `docs/adr/030-conversation-capsule.md`, `docs/adr/029-context-compilation-request-shaped-memory.md`, `docs/architecture/conversational-ui.md`, `docs/architecture/conversational-stream.md`, `tickets/conversational-ui/**`  
**Must not edit:** `intent_router.py` phrase families · new C09 tools · richer `world.explain` · timer / decompose capabilities · tone memory

**Hard depends:** [C09](./C09-llm-conversational-boundary.md) compiler ([ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md))  
**Soft (~):** [C09b](./C09b-discourse-focus.md) focus vs objects  
**Architecture:** [ADR-030](../../docs/adr/030-conversation-capsule.md)

## Goal

Enigma should understand elliptical follow-ups by carrying forward the live conversational **frame**, without retaining the transcript as truth or adding phrase-specific routing.

**Compile the conversation, not just the sentence.**

## Frozen rules

1. The capsule carries continuity. The compiler grants context. The world establishes truth.
2. Evidence and constraints may inherit. Authority must be re-earned.
3. Requests resolve. Conversational frames decay.
4. The capsule may recover the question. It may not recover the answer.

## Loop

```text
previous capsule + new utterance
        ↓
INHERIT live frame unless contradicted
        ↓
re-earn authority
        ↓
compile
        ↓
tools + response
        ↓
ASSESS SATISFIED | PARTIAL | UNSATISFIED
        ↓
REDUCE next capsule
```

Underspecification (not more `_FOLLOW_UP` regex):

```text
would otherwise compile to GENERAL_KNOWLEDGE / CONVERSATION_ONLY / empty private surface
AND live grounded frame exists
AND new utterance does not contradict it
```

## Deliverables

- [x] Typed `ConversationCapsule` with `RequestKind` goal, request vs decaying frame, `previous_authority` metadata (not a grant)
- [x] Inherit evidence/constraints in `interpret_request`; re-earn authority every turn
- [x] Post-turn satisfaction assessment + reducer (`tool success ≠ request satisfaction`)
- [x] Tiny non-authoritative capsule on the wire; no providers/tools dump in `working_set`
- [x] Tests: `apps/api/tests/test_c09_conversation_capsule.py`
- [x] Life Script `alex_jan19_conversation_capsule.script.yaml`
- [x] ADR-030

## Out of scope

Richer `world.explain` / `subject_summary`; email importance semantics; `timer.*` / `support.decompose`; capability-promise policing; fat PRIVATE_QUERY floor; EXTERNAL_WORLD; work-scope in `agenda.get`; new English phrase families; retention; tone memory.

Those are later product contracts. They are not unfinished C09c.

## Freeze

The capsule loop is closed. Flagship proof: `"ffs"` recovers the unresolved private request, re-grounds, and requires a fresh private tool — no ranking from transcript. Do not add `_FOLLOW_UP` phrases, inherit authority, or treat tool 200 as request satisfaction. C15 may consume `public_view()`; it must not amend this object. [C16](./C16-attested-completion-invalidates-next-action.md)–[C23](./C23-continuity-integrity-life-script.md) likewise consume the capsule; they must not put receipts, next-action invalidation, or `active_thread` fields on it. [C24](./C24-read-only-evidence-worker.md) dispatches a read-only evidence envelope after compile; it must not bypass or amend this object.

## Definition of done

Given a live conversational goal, subject, evidence regime and constraints, elliptical or corrective follow-up turns inherit that frame before request interpretation. Tool success is distinguished from request satisfaction. Unresolved goals survive into the next capsule; satisfied or contradicted state is reduced away. The capsule may resolve language but cannot establish world truth or grant authority.
