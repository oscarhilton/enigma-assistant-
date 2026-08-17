# ADR-032: Action ledger — execution receipts and verification-not-action

**Status:** Accepted  
**Date:** 2026-08-17

> **An external-action claim requires a matching execution receipt.**
>
> **“Did you do it?” inspects the ledger. It never starts another action.**
>
> **Absence of a receipt is uncertain, not yes.**

## Context

[ADR-020](./020-llm-conversational-boundary-not-truth.md) already holds action success in Enigma core: verified execution + Assist pipeline. [ADR-028](./028-conversational-constitution-attestation-dialogue-support.md) already holds that user *reports* write world evidence. [ADR-010](./010-next-action-not-attention.md) already holds Next Action as a derived projection, not chat.

A 61-turn Demo forensic session showed the conversational layer still speaking as if it had acted:

1. Turns 56 and 59 claimed the team would be notified with no messaging tool and no receipt.
2. Turn 60 “Did you actually do it?” invoked `assist.propose` for the token inventory instead of inspecting what had been done.

That is the LLM treating prose as execution, and treating a verification question as a new Assist. The capsule ([ADR-030](./030-conversation-capsule.md)) must not absorb this. The capsule recovers the question; it does not store receipts, invalidate next actions, or answer “did you do it?”

This sprint is **Conversation Continuity and Action Integrity** — before adding more assists. Do not fold receipts into [C09c](../../tickets/conversational-ui/C09c-conversation-capsule.md) or live [C15](../../tickets/conversational-ui/C15-semantic-bootstrap-capsule.md) bootstrap.

## Decision

### Action ledger

Session world keeps an append-only **action ledger** of execution receipts. A receipt is produced only when Enigma actually performed (or verifiably failed) an external or world-mutating act:

| Field | Meaning |
| --- | --- |
| `receipt_id` | Stable id |
| `action_kind` | `notify` · `send` · `book` · `mark` · `start` · `attest` · … |
| `target_id` | Obligation / subject |
| `status` | `performed` · `failed` · `not_attempted` |
| `capability` | Tool that executed (`assist.approve`, `world.record_user_attestation`, …) |
| `recorded_at` | Simulation clock |

User attestation writes a receipt of kind `attest` (evidence, not an external send). Assist SATISFIES writes a receipt of the executed kind. A draft Assist ADVANCES does **not** mint a `sent` / `booked` / `notified` receipt ([C07b](../../tickets/conversational-ui/C07b-assist-completed-not-task-completed.md)).

The ledger is world/session state. It is **not** a `ConversationCapsule` field. [C18](../../tickets/conversational-ui/C18-active-thread-record.md) `active_thread` may *point at* `last_execution_receipt`; it must not own the ledger.

### Claim fence

Any user-facing language that asserts Enigma **sent / started / booked / marked / notified** requires a matching receipt with `status=performed` for that kind and target. No receipt → the respond phase may not emit that claim. Orchestration must rewrite or deny the turn rather than hope the model is modest.

Tool HTTP 200 is not a receipt. Capsule SATISFIED is not a receipt. Assistant commitment in `active_thread` is not a receipt.

### Verification is not action

Questions of the form “did you do it?” / “did you actually send that?” / “has that gone out?” are **VERIFICATION**. They:

1. Classify as verification, not `ACTION_REQUEST` / PREPARE.
2. Call a ledger inspect capability (`action.inspect` or equivalent).
3. Answer only from the receipt: **yes**, **no**, or **uncertain**.
4. Must not invoke `assist.propose`, `assist.approve`, or any other initiating tool.

Uncertain is the honest default when no receipt exists. Do not invent a send to make the answer yes.

### Three hard invariants (sprint)

1. A completed or superseded task cannot be returned by `next_action.get` ([C16](../../tickets/conversational-ui/C16-attested-completion-invalidates-next-action.md) · [ADR-010](./010-next-action-not-attention.md)).
2. An external-action claim cannot be emitted without a matching execution receipt (this ADR).
3. “Did you do it?” can only answer from that receipt: yes, no, or uncertain (this ADR).

## Consequences

- `speech_acts` gains VERIFICATION (constitution, not an `intent_router` phrase family). Compromised `assist.propose` on a verification turn is rewritten or denied.
- The compiled wire may name the inspect capability when the request is verification ([ADR-029](./029-context-compilation-request-shaped-memory.md)). It must not hide it.
- Fireworks is not solely at fault: useful recent dialogue can ground a turn; zero dialogue / wrong profile still produces chatbot sludge. The ledger is the floor when the model claims an act.
- Related: [ADR-010](./010-next-action-not-attention.md) · [ADR-020](./020-llm-conversational-boundary-not-truth.md) · [ADR-028](./028-conversational-constitution-attestation-dialogue-support.md) · [ADR-029](./029-context-compilation-request-shaped-memory.md) · [ADR-030](./030-conversation-capsule.md) · [ADR-033](./033-bounded-subtask-workers.md) · [C17](../../tickets/conversational-ui/C17-execution-receipts-verification-ledger.md)

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Store receipts on `ConversationCapsule` | Capsule is frozen conversation state; receipts are world facts ([ADR-030](./030-conversation-capsule.md)) |
| Treat Assist 200 / capsule SATISFIED as “done” | Tool success ≠ request satisfaction ≠ execution |
| Let the model answer “did you do it?” from `recent_dialogue` | Chat is not the ledger; it will propose another Assist |
| Add `email.send` / `timer.start` to make the claims true | This sprint is integrity of existing acts, **before more assists** |
| Fold into C15 semantic bootstrap | Bootstrap interprets language; it does not grant execution or receipts |
| Replace this ledger with an action-verification personality | Invariant first; worker is later shape ([ADR-033](./033-bounded-subtask-workers.md)) |
