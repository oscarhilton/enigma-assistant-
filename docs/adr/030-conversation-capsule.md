# ADR-030: Conversation capsule — compile the conversation, not the sentence

**Status:** Accepted  
**Date:** 2026-08-17

> **The capsule carries continuity. The compiler grants context. The world establishes truth.**
>
> **Evidence and constraints may inherit. Authority must be re-earned.**
>
> **Requests resolve. Conversational frames decay.**
>
> **The capsule may recover the question. It may not recover the answer.**

## Context

[ADR-029](./029-context-compilation-request-shaped-memory.md) compiles a *request* into a justified working set. Live Demo dumps showed the compiler succeeding on complete utterances (`"what's on today?"` → `PRIVATE_WORLD` / `READ` / `agenda.get`) and then failing on elliptical follow-ups (`"and?"`, `"what should I do with this free time?"`, `"ffs"`), which fell through to `GENERAL_KNOWLEDGE` / `CONVERSATION_ONLY` with zero tools.

That is short attention becoming short-term amnesia. Expanding `_FOLLOW_UP` phrase lists would recreate the frozen `intent_router` problem. The missing object is **continuation state of the human interaction** — not a transcript, not world truth, not an authority grant.

## Decision

A typed `ConversationCapsule` lives on session `ConversationContext`. It is conversation state. It is not world state.

```text
previous capsule + new utterance
        ↓
INHERIT evidence and constraints unless contradicted
        ↓
re-earn authority from this utterance
        ↓
context / authority compiler
        ↓
tools + response
        ↓
ASSESS request satisfaction
        ↓
REDUCE next capsule
        ↺
```

### Two lifetimes

| Object | Lives until | SATISFIED does |
| --- | --- | --- |
| **Request** (`unresolved_request` / `active_goal: RequestKind`) | answered, contradicted, or replaced | **clear the request** |
| **Frame** (domain, temporal/source/scope, subject) | TTL or contradiction | **not** necessarily clear the frame |

`"what's on today?"` can SATISFY the agenda request while leaving `PRIVATE_WORLD` / `today` live so `"what should I do with this free time?"` still inherits the frame.

`active_goal` is a `RequestKind` enum (`agenda`, `next_work`, `important_from_source`, `support_explain`, `attest`). It is not a prose summary. No gist in v1.

### Inheritance

Inherit the live grounded frame when:

```text
the utterance would otherwise compile to GENERAL_KNOWLEDGE / CONVERSATION_ONLY / empty private surface
AND a live grounded PRIVATE_WORLD frame exists
AND the new utterance does not contradict it
```

`"and?"`, `"what else?"`, `"who do I ask?"`, `"ffs"` are not magical phrases. Their meaning emerges because the conversation has a frame (and maybe an unresolved request) to continue.

Contradiction (fresh interpretation wins; private modules do not leak): independent general knowledge (`"why is the sky blue?"`), and self-contained new complete private requests.

**Authority is never inherited as a grant.** `previous_authority` is last-turn metadata. `APPROVE` / `EXECUTE` / `PREPARE` are re-earned from this utterance (and live `APPROVE_CONFIRMATION`). SUPPORT is inferred again from capsule goal + utterance, not copied.

### Tool success ≠ request satisfaction

`source.recent` may succeed while `"tell me what's important"` remains PARTIAL. Assessment is the sibling of `compose_follow_up_tools`: did the operation succeed vs did it answer the human.

Uncertain → PARTIAL. Do not clear the goal.

### Recover the question, not the answer

Recent dialogue and the capsule may disambiguate `"ffs"`. A response that ranks private work still requires a **fresh** authoritative private tool result this turn (`attention.get_current` / `next_action.get` / `agenda.get`). Chat history must not become world truth.

After attestation: the world write is authoritative; the capsule may keep TOKEN as subject; it must not store `TOKEN.completed`. `"what else is on?"` inherits the **frame**, not the attest goal, and infers a fresh `agenda` / `next_work` request. Authority is re-earned as READ.

## Consequences

- `interpret_request` inherits before domain classification. `intent_router` phrase families stay frozen.
- `run_orchestrator_turn` reduces the capsule after tools. SATISFIED clears the request; the frame decays on TTL or generic-knowledge contradiction.
- The compiled working set may include a tiny non-authoritative capsule. The audit manifest stays off the LLM user message ([ADR-029](./029-context-compilation-request-shaped-memory.md)).
- Execution receipts, next-action invalidation, and “did you do it?” live on the action ledger / session overlay — **not** on this object ([ADR-032](./032-action-ledger-execution-receipts-verification.md) · [C17](../../tickets/conversational-ui/C17-execution-receipts-verification-ledger.md) · [C16](../../tickets/conversational-ui/C16-attested-completion-invalidates-next-action.md)). Thread compactness is a sibling `active_thread` ([C18](../../tickets/conversational-ui/C18-active-thread-record.md)).
- Related: [ADR-020](./020-llm-conversational-boundary-not-truth.md) · [ADR-028](./028-conversational-constitution-attestation-dialogue-support.md) · [ADR-029](./029-context-compilation-request-shaped-memory.md) · [ADR-031](./031-semantic-bootstrap-compiler-grants-context.md) · [ADR-032](./032-action-ledger-execution-receipts-verification.md) · [ADR-033](./033-bounded-subtask-workers.md) · [C09c](../../tickets/conversational-ui/C09c-conversation-capsule.md)

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Expand `_FOLLOW_UP` / `intent_router` English | Frozen; phrase lists do not scale to `"ffs"` |
| Inherit authority with the frame | `"Yes, approve that."` then `"And the other one?"` would escalate |
| Clear the frame when the request is SATISFIED | Breaks `"what's on today?"` → `"what should I do with this free time?"` |
| `active_goal: str` prose | Becomes a recursive summary; llama-farm drift |
| Send six turns of transcript instead | Reconstructability leak; SEC-07 |
| Treat tool 200 as conversational success | `source.recent` congratulates itself while Alex shouts AND??? |
| Store execution receipts or completed-task flags on the capsule | World/session ledger and next-action overlay ([ADR-032](./032-action-ledger-execution-receipts-verification.md)); capsule recovers the question, not the answer |
| Host subtask workers on the capsule | Workers consume `public_view()` ([ADR-033](./033-bounded-subtask-workers.md)); they do not live on this object |
