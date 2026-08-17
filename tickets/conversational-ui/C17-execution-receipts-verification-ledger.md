# C17 — Execution receipts and verification-from-ledger

**Status:** todo  
**Branch:** `ticket/C17-execution-receipts-verification-ledger`  
**Domain:** conversational-ui  
**May edit:** `apps/api/src/personal_enigma/api/action_ledger.py` (new), `apps/api/src/personal_enigma/api/speech_acts.py` (VERIFICATION act only), `apps/api/src/personal_enigma/api/demo_orchestrator.py` (verification routing / claim fence), `apps/api/src/personal_enigma/api/demo_tools.py` (register `action.inspect` + mint receipts on attested/assist execute only), `apps/api/src/personal_enigma/api/demo_assist.py` (receipt on SATISFIES only), `apps/api/src/personal_enigma/api/demo_attestation.py` (attest receipt only), `apps/api/tests/test_c17_*.py`, `docs/adr/032-*.md`, `docs/adr/020-*.md` / `028-*.md` (see-also only), `docs/architecture/conversational-ui.md` (pointer), `tickets/conversational-ui/**`

**Must not edit:** `ConversationCapsule` / ADR-030 loop · `intent_router.py` phrase families · C15 bootstrap · new Assist *kinds* / `email.send` / `timer.*` · C16 next-action overlay (sibling) · C09c frozen mechanism

**Hard depends:** [C09](./C09-llm-conversational-boundary.md) tool registry · [ADR-032](../../docs/adr/032-action-ledger-execution-receipts-verification.md)  
**Soft (~):** [C16](./C16-attested-completion-invalidates-next-action.md) (attest receipts) · [C07b](./C07b-assist-completed-not-task-completed.md) · [C18](./C18-active-thread-record.md) may point at `last_execution_receipt`

**Architecture:** [ADR-032](../../docs/adr/032-action-ledger-execution-receipts-verification.md) · [ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md) · [ADR-028](../../docs/adr/028-conversational-constitution-attestation-dialogue-support.md)

## Goal

**Before more assists.** Enigma must not claim it sent, started, booked, or marked anything unless a matching execution receipt exists. “Did you actually do it?” must inspect that ledger — never start another Assist.

Forensic dump: [`packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt`](../../packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt) ([C23](./C23-continuity-integrity-life-script.md)).

Exact lines:

- Turn 56: `woah there I just meant let the team know` → dump “Got it—I’ll let the team know.” (no tool, no receipt)
- Turn 59: `yes` → dump “I’ll go ahead and let the team know what you mentioned.” (no tool, no receipt). Same user string as turns 4 and 42; C23 gates the claim on turn 56.
- Turn 60: `did you actually do it?` → dump `assist.propose` for the token inventory
- Turn 57: `did you really let them know?` → dump lost “them” (C18) instead of inspecting the ledger

## Frozen rules

1. Receipts live on the session action ledger — **not** on `ConversationCapsule`.
2. Tool HTTP 200 ≠ request satisfaction ≠ execution receipt.
3. VERIFICATION is a speech act. It is not PREPARE / ACTION_REQUEST.
4. Answers from the receipt only: **yes** / **no** / **uncertain**. No receipt → uncertain, not yes.
5. Do not add send/timer capabilities to make false promises true.

## Deliverables

- [ ] Append-only `action_ledger` on the Demo session (shape in ADR-032)
- [ ] Mint receipts on verified Assist SATISFIES and on `world.record_user_attestation`; never on draft ADVANCES for `sent`/`notified`/`booked`
- [ ] `action.inspect` (or equivalent public capability) reads the ledger for a target / last pending action
- [ ] Constitution: verification questions cannot execute `assist.propose` / `assist.approve`
- [ ] Respond fence: `sent`/`started`/`booked`/`marked`/`notified` language requires `status=performed` receipt; otherwise rewrite or deny
- [ ] Tests: notify-claim without receipt fails; “did you do it?” → inspect, not propose; yes/no/uncertain from fixture receipts

## Out of scope

Next-action invalidation ([C16](./C16-attested-completion-invalidates-next-action.md)); active-thread compactness ([C18](./C18-active-thread-record.md)); multi-intent ([C19](./C19-multi-intent-decompose.md)); capability contract copy ([C20](./C20-capability-contract-on-wire.md)); more assists; C09c; C15 live bootstrap. An **action-verification worker** is a later implementation shape ([ADR-033](../../docs/adr/033-bounded-subtask-workers.md) · [C24](./C24-read-only-evidence-worker.md) is the first worker, and it is not this ticket). This ticket lands the ledger in the parent.

## Definition of done

Zero unsupported action claims on the C17 tests. `did you actually do it?` never initiates an action. Invariant 2 and 3 of ADR-032 hold without putting receipts inside the capsule. Gate: [C23](./C23-continuity-integrity-life-script.md).
