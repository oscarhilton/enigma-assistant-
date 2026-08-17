# C16 — Attested completion materializes; next_action cannot resurface

**Status:** in_progress  
**Branch:** `ticket/C16-attested-completion-invalidates-next-action`  
**Domain:** conversational-ui  
**May edit:** `apps/api/src/personal_enigma/api/demo_attestation.py`, `apps/api/src/personal_enigma/api/demo_assist.py` (`overlay_session_world` / next-action filter only), `apps/api/src/personal_enigma/api/demo_tools.py` (`next_action.get` / `next_action.get_alternatives` / attestation execute only), `apps/api/src/personal_enigma/api/demo_intents.py` (next-action overlay only), `apps/api/src/personal_enigma/api/routes/demo.py` (session overlay / cache invalidation only), `apps/api/tests/test_c09_user_attestation.py`, `apps/api/tests/test_demo_projection.py`, `packages/evaluation/scripts/alex_jan19_user_attestation.script.yaml`, `packages/attention/src/personal_enigma/attention/projection.py` (completed-id filter only, if the cache lives here), `docs/architecture/next-action.md`, `docs/adr/010-next-action-not-attention.md` (invariant sentence), `docs/architecture/conversational-ui.md` (pointer), `tickets/conversational-ui/**`

**Must not edit:** `intent_router.py` phrase families · `ConversationCapsule` / ADR-030 loop · new C09 tools · `timer.*` / `email.send` · C15 bootstrap · more Assist kinds · C09c frozen files except the overlay/next_action lines named above

**Hard depends:** [C09](./C09-llm-conversational-boundary.md) attestation tool ([ADR-028](../../docs/adr/028-conversational-constitution-attestation-dialogue-support.md))  
**Soft (~):** [C07b](./C07b-assist-completed-not-task-completed.md) (complementary invariant — do not wait) · [C23](./C23-continuity-integrity-life-script.md) replay

**Architecture:** [ADR-028](../../docs/adr/028-conversational-constitution-attestation-dialogue-support.md) · [ADR-010](../../docs/adr/010-next-action-not-attention.md) · [ADR-032](../../docs/adr/032-action-ledger-execution-receipts-verification.md) invariant 1

## Goal

**Before more assists.** If Alex reports the token audit complete, that write must update materialized task state and invalidate any cached next-action projection so TOKEN cannot be recommended again.

Forensic dump: [`packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt`](../../packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt) ([C23](./C23-continuity-integrity-life-script.md)).

Exact lines:

- Turn 12: `OK I have done the design work!` → `world.record_user_attestation` (“Noted — I'll treat Draft colour + spacing token inventory as done.”)
- Turn 38: `we already picked right? is it in the calendar? can we make the email?` → dump recites TOKEN as “Strong next action” via `agenda.get`
- Turn 49: `whats next?` → dump `next_action.get` returns “Draft colour + spacing token inventory”

Existing Life Script `alex_jan19_user_attestation` already covers the *immediate* `"What's next?"`. This ticket is the **later-turn** hole: intervening conversation must not resurrect a completed or superseded task.

## Invariant

**A completed or superseded task cannot be returned by `next_action.get`.**

Complementary to C07b:

| Ticket | Invariant |
| --- | --- |
| **C07b** | ASSIST COMPLETED ≠ TASK COMPLETED (do not over-complete) |
| **C16** | ATTESTED COMPLETED ⇒ task leaves next-action and stays out (do not under-complete) |

`current_subject_id` may remain TOKEN (“what did you just finish?”). `current_next_action_id` must not point at a non-action. Capsule must not store `TOKEN.completed` ([ADR-030](../../docs/adr/030-conversation-capsule.md)).

## Frozen rules

1. Attestation is evidence (`world.record_user_attestation`). It is not Assist.
2. Frozen Demo checkpoints are never mutated; session overlay is the write.
3. After COMPLETED/CANCELLED, re-project next actions from the overlay. Do not answer `next_action.get` from a pre-attestation cache or from `recent_dialogue`.
4. OPEN supersedes a prior completion and may return the task to next-action.

## Deliverables

- [x] Attestation COMPLETED/CANCELLED updates materialized overlay (`completed_item_ids` / equivalent) **and** drops any cached `NextActionView` for that `target_id`
- [x] `next_action.get` / `get_alternatives` re-overlay on every call; completed/superseded ids cannot appear
- [x] Model copy that recites TOKEN as next work after attestation fails even when no tool ran (`must_not · recites_completed_as_next_action`)
- [x] Extend `alex_jan19_user_attestation` with intervening turns (agenda / social / other subject) then `"What's next?"` / equivalent — TOKEN still excluded
- [x] Tests: immediate + delayed resurfacing; OPEN restores eligibility

## Out of scope

Execution receipts / “did you do it?” ([C17](./C17-execution-receipts-verification-ledger.md)); active-thread slots ([C18](./C18-active-thread-record.md)); more assists; C09c capsule fields; C15 live bootstrap; `intent_router` English.

## Definition of done

Given a USER_ATTESTATION that TOKEN is COMPLETED, every later `next_action.get` in that session omits TOKEN until a superseding OPEN. Dump turns 38 and 49 recommending completed work are a failed test, not a model quirk. Gate: [C23](./C23-continuity-integrity-life-script.md).
