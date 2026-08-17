# C27 — Handoff and turn contract

**Status:** todo  
**Branch:** `ticket/C27-handoff-turn-contract`  
**Domain:** conversational-ui  
**May edit:** `apps/api/src/personal_enigma/api/context_compilation.py`, `apps/api/src/personal_enigma/api/conversation_context.py`, `apps/api/src/personal_enigma/api/demo_orchestrator.py`, `apps/api/tests/test_c27_*.py`, `docs/architecture/conversational-ui.md`, `tickets/conversational-ui/**`

**Must not edit:** `ConversationCapsule` fields or reducer · `intent_router.py` phrase families · approval inheritance rules

**Hard depends:** [C26](./C26-grounded-assertions-epistemics.md) proposition substrate available  
**Soft (~):** [C18](./C18-active-thread-record.md) · [C09c](./C09c-conversation-capsule.md)

## Goal

Keep long conversation continuity without turning continuity into truth.

## Deliverables

- [ ] Add a compact handoff structure for progress, unresolved work, and natural continuation
- [ ] Add a small turn contract exposing current request, authority, available capabilities, and factual boundaries
- [ ] Keep dialogue, handoff, capsule, and evidence distinct on the wire
- [ ] Tests prove model replacement can continue a job without transcript-as-truth leakage

## Definition of done

`"and?"` / `"ffs"` / clause continuations can inherit progress and missing evidence without inheriting factual assumptions or elevated authority.
