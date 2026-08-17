# C20 — Capability contract on the compiled wire

**Status:** todo  
**Branch:** `ticket/C20-capability-contract-on-wire`  
**Domain:** conversational-ui  
**May edit:** `apps/api/src/personal_enigma/api/context_compilation.py` (capability contract module on the compiled envelope), `apps/api/src/personal_enigma/api/demo_tools.py` (`DENIED_REMOTE_CAPABILITIES` / allowed-tool listing as data for the contract only), `apps/api/tests/test_c09_context_compilation.py`, `apps/api/tests/test_c20_*.py`, `docs/adr/029-*.md` (contract subsection), `docs/architecture/conversational-ui.md` (pointer), `tickets/conversational-ui/**`

**Must not edit:** `intent_router.py` · `ConversationCapsule` · `semantic_bootstrap.py` / C15 merge hook · new product capabilities (`timer.*`, `email.send`) · C09c inherit loop

**Hard depends:** [C09](./C09-llm-conversational-boundary.md) compiler ([ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md))  
**Soft (~):** [C15](./C15-semantic-bootstrap-capsule.md) in_progress on compile merge — do not collide; this ticket owns the **contract object**, not bootstrap · [C17](./C17-execution-receipts-verification-ledger.md) claim fence · [C19](./C19-multi-intent-decompose.md)

**Architecture:** [ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md) · [ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md) · [ADR-032](../../docs/adr/032-action-ledger-execution-receipts-verification.md)

## Goal

**Before more assists.** The model must receive a clear capability contract **before** composing a response, so it cannot promise a timer or an email send that Enigma cannot perform.

C09c listed capability-promise policing as a later product contract, not unfinished capsule work. This is that ticket.

Forensic dump: [`packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt`](../../packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt) ([C23](./C23-continuity-integrity-life-script.md)).

Exact lines:

- Turn 8: `I need help getting started. can we make a list of actions and start a timer when im ready?`
- Turn 9: `you need to get better at understanding me` — dump restated the timer plan (“just let me know when you want to kick off the timer”)
- Turn 10: `start timer for 10 mins` — dump correctly said it cannot start a timer (keep this honesty; do not add `timer.*`)
- Turn 42: `yes` — dump drafted a reservation email and offered “if you’d like me to send this on your behalf”
- Turn 43: `send it` — dump correctly said it cannot send (keep this honesty; do not add `email.send`)

## Frozen rules

1. Absence of a tool on the registry is not enough. The compiled user/working set must state **allowed this turn** and **named absences** for common false promises (`timer`, `email.send` / notify, filesystem, arbitrary network).
2. The contract is compiler output ([ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md)). The model does not invent capabilities. Enigma does not add `timer.*` to make turn 9 true.
3. Do not hide a capability the request requires (existing compiler recall rule). Do not imply a capability that is denied.
4. Not C15: bootstrap still receives no private world and grants no authority.

## Deliverables

- [ ] Compiled envelope includes `capability_contract`: `{allowed: [...], unavailable: [...]}` (names stable, tiny, remote-safe)
- [ ] Tests: timer/email-send absent from allowed and present in unavailable on a default Demo compile; respond/orchestration must not claim those acts ([C17](./C17-execution-receipts-verification-ledger.md) fence may consume this)
- [ ] ADR-029 consequence: capability contract is part of compilation, not prompt folklore
- [ ] Existing `test_c09_context_compilation.py` stays green

## Out of scope

Implementing timers or mail send; C09c; C15 live Fireworks bootstrap; phrase families; active-thread ([C18](./C18-active-thread-record.md)).

## Definition of done

Before the planner composes, the wire states what Enigma can and cannot do this turn. False timer/email promises in C20 tests are compiler/contract failures, not “the model got confused.” Gate: [C23](./C23-continuity-integrity-life-script.md).
