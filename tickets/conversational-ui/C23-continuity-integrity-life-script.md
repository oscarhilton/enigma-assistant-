# C23 — Continuity and action-integrity Life Script (61-turn sprint gate)

**Status:** landed · frozen as a specification (gate red until C16–C21)  
**Branch:** `ticket/C23-continuity-integrity-life-script`  
**Domain:** conversational-ui  
**May edit:** `packages/evaluation/scripts/alex_jan19_continuity_integrity.script.yaml` (new), `packages/evaluation/fixtures/forensic/**` (dump + utterance index), `packages/evaluation/src/personal_enigma/evaluation/life_scripts/schema.py` (new public-effect keys only), `packages/evaluation/src/personal_enigma/evaluation/life_scripts/runner.py` (assert those keys), `packages/evaluation/tests/test_life_scripts.py`, `tickets/conversational-ui/**`, `docs/architecture/conversational-ui.md` (episode list)

**Must not edit:** C09 production tools / orchestrator (product lands in C16–C21) · `intent_router.py` · C09c · C15 · C13 YAML-repeat harness · inventing dump utterances

**Hard depends:** [C16](./C16-attested-completion-invalidates-next-action.md) · [C17](./C17-execution-receipts-verification-ledger.md)  
**Soft (~):** [C18](./C18-active-thread-record.md) · [C19](./C19-multi-intent-decompose.md) · [C20](./C20-capability-contract-on-wire.md) · [C21](./C21-grounded-values-no-invented-facts.md) · [C12](./C12-life-scripts.md) conventions · [C22](./C22-adhd-response-shape.md) (do not block)

**Contract:** [C12](./C12-life-scripts.md) frozen rules. Not [C13](./C13-life-script-reliability.md) (C13 repeats *existing* YAML).

## Dump (source of truth)

| File | What |
| --- | --- |
| [`packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt`](../../packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt) | Full 61-turn forensic UI blob (Demo Alex / `alex_v1`) |
| [`packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.turns.yaml`](../../packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.turns.yaml) | Compact index: exact user lines + gate tags |
| `apps/web/src/enigma/forensicDump.ts` | Formatter only — not the dump |

Do not paste the forensic UI blob into tickets. Quote user lines from the turn index.

## Goal

Sprint acceptance for **Conversation Continuity and Action Integrity** — before more assists. Replay the dump's gate utterances through the real C09 `DemoSession.handle_message` path.

Life Script: [`packages/evaluation/scripts/alex_jan19_continuity_integrity.script.yaml`](../../packages/evaluation/scripts/alex_jan19_continuity_integrity.script.yaml). Script order is a coherent world (attest TOKEN before later `"whats next?"`); dump order lives in the turn index. C09c / ADR-030 stays frozen.

## Sprint acceptance (must hold)

Exact dump lines. No paraphrases.

| Class | Dump turn | User (exact) | Ticket |
| --- | --- | --- | --- |
| Attest completed | 12 | `OK I have done the design work!` | [C16](./C16-attested-completion-invalidates-next-action.md) |
| Completed work resurfaces | 38 | `we already picked right? is it in the calendar? can we make the email?` (dump recites TOKEN via `agenda.get`) | [C16](./C16-attested-completion-invalidates-next-action.md) |
| Completed work resurfaces | 49 | `whats next?` (dump `next_action.get` → TOKEN) | [C16](./C16-attested-completion-invalidates-next-action.md) |
| Claim notify, no receipt | 56 | `woah there I just meant let the team know` | [C17](./C17-execution-receipts-verification-ledger.md) |
| Claim notify, no receipt | 59 | `yes` (after dump turn 58 offered to notify) | [C17](./C17-execution-receipts-verification-ledger.md) |
| Verification → Assist | 60 | `did you actually do it?` (dump `assist.propose`) | [C17](./C17-execution-receipts-verification-ledger.md) |
| `this free time` | 2 | `what should I do with this free time?` | [C18](./C18-active-thread-record.md) |
| `and?` | 18 | `and?` | [C18](./C18-active-thread-record.md) |
| `the colours` | 53 | `where did you get the colours from` | [C18](./C18-active-thread-record.md) |
| `someone` / `them` | 55 / 57 | `Should I let someone know?` / `did you really let them know?` | [C18](./C18-active-thread-record.md) |
| All clauses of turn 38 | 38 | `we already picked right? is it in the calendar? can we make the email?` | [C19](./C19-multi-intent-decompose.md) |
| Invented restaurants/addresses | 37 | `go for it!` | [C21](./C21-grounded-values-no-invented-facts.md) |
| Invented design-token colours | 51 | `ok lets go` | [C21](./C21-grounded-values-no-invented-facts.md) |
| Timer promise then impossible | 9 / 10 | `you need to get better at understanding me` / `start timer for 10 mins` | [C20](./C20-capability-contract-on-wire.md) |
| Offer to send, no send capability | 42 | `yes` (dump offered to send the reservation email) | [C20](./C20-capability-contract-on-wire.md) |
| Concise action-oriented default | 2, 6, 14, 55 | essays/tables — **soft**; do not block | [C22](./C22-adhd-response-shape.md) |

Turn 59's user line is also `yes` (same string as turns 4 and 42). The Life Script uses dump turn 42's `yes` for the send-offer class; turn 56 already gates the notify claim. Do not encode turn 59 as a second planner key.

## Frozen rules (C12)

1. Scripts speak like Alex, never like Enigma internals.
2. Assertions observe public effects + structured boundaries (`action.inspect`, `next_action.get`, `world.record_user_attestation` are allowed capability names).
3. Model-specific behaviour is replaceable; world truth is not.
4. Not falling back is not the same as understanding.

Do not encode router intents, orchestrator branches, or regex IDs.

## Deliverables

- [x] `packages/evaluation/scripts/alex_jan19_continuity_integrity.script.yaml`
- [x] Dump + compact utterance index under `packages/evaluation/fixtures/forensic/`
- [x] Public-effect keys: `covers`, `must_not · claim_action_without_receipt`, `must_not · verification_initiates_assist`, `must_not · invent_private_world_value`, `must_not · promise_unavailable_capability`, `must_not · lose_referent` (plus existing `current_next_action_excludes`)
- [x] Deterministic CI path (load + utterance contract always; full episode xfail on dump turn 38 `covers` until [C19](./C19-multi-intent-decompose.md); live Fireworks optional, not C13 `--runs 5`)
- [x] Dump attachment note in the YAML header

## Out of scope

Implementing C16–C21 product code in this ticket; C13 reliability stats; C15; more assists; C09c; C22 as a hard gate; bounded workers ([C24](./C24-read-only-evidence-worker.md) / [ADR-033](../../docs/adr/033-bounded-subtask-workers.md) — after P0, do not block this gate).

## Dump turns not in the Life Script

Present in the dump, not a P0/P1 gate line (meta, sludge, or duplicate `yes`): 3–7, 11, 15–16, 19, 21–24, 26–36, 39–41, 44–47, 52, 54, 58, 59, 61. Turn 20 `ffs` is in the script as intervening repair ([C24](./C24-read-only-evidence-worker.md) later). Turn 36 is a stage direction, not spoken Alex.

## Definition of done

The Life Script fails the dump's failure classes until C16–C21 land, then passes deterministically. Gate utterances are the dump's exact user lines. P2 brevity does not block this gate.
