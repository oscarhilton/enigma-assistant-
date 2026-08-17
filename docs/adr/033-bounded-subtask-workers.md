# ADR-033: Bounded subtask workers — specialist hands, not personalities

**Status:** Accepted  
**Date:** 2026-08-17

> **One agent speaks. Workers fetch. The parent still decides.**
>
> **A worker may return claims and evidence ids. It may not say “I sent it.”**
>
> **Delegation is OpenClaw-like plumbing. Authority compilation stays Enigma.**

## Context

At 10k feet ChatGPT, OpenClaw, and Enigma share a loop: message → assemble context → select capabilities → model → tool calls → results → response → persist.

- **ChatGPT:** similar product intent and high-level mechanics. Enigma’s explicit compiler ([C15](../../tickets/conversational-ui/C15-semantic-bootstrap-capsule.md) → [ADR-029](./029-context-compilation-request-shaped-memory.md) request / evidence / authority → minimal context + permitted tools → model/tool loop → [ADR-030](./030-conversation-capsule.md) continuity) is a typed policy engine. ChatGPT behaviour is public; internal equivalents of ADR-029 / C09c / C15 are unknown.
- **OpenClaw (public):** similar runtime plumbing (gateway, sessions, context assembly, inference, tools, persistence). Different control philosophy: OpenClaw is an agent gateway/runtime; Enigma is a private-world **attention and authority** system. Transcript recovers the question; world evidence must be reacquired.

The `"ffs"` contract is that split: conversational context recovers what Alex still wants; current world evidence, authority to read, and authority to act are compiled again — not answered from the transcript.

This ADR does **not** amend the capsule ([ADR-030](./030-conversation-capsule.md) remains frozen). It does **not** replace P0 action-integrity invariants ([ADR-032](./032-action-ledger-execution-receipts-verification.md)). Workers are a later implementation shape around that constitution.

## Decision

**One conversational mind.** The parent orchestrator speaks to the user and owns the active thread ([C18](../../tickets/conversational-ui/C18-active-thread-record.md)). Subagents do isolated work behind it. They are not extra personalities, not a polish LLM, not [C11](../../tickets/conversational-ui/C11-tone-memory.md).

```text
User
  ↓
C15 semantic bootstrap (optional)
  ↓
ADR-029 compiler (request · evidence · authority)
  ↓
Conversation orchestrator
  ├── evidence worker
  ├── decomposition worker
  ├── explanation worker
  └── action-verification worker
  ↓
One coherent response
```

### Parent keeps (do not delegate)

| Concern | Why |
| --- | --- |
| Referent resolution | Subject selection ≠ capability selection ([ADR-020](./020-llm-conversational-boundary-not-truth.md)) |
| Authority decisions | Compiler grant, not worker improvisation ([ADR-029](./029-context-compilation-request-shaped-memory.md)) |
| Current-subject ownership | Discourse focus ([C09b](../../tickets/conversational-ui/C09b-discourse-focus.md)) |
| Satisfaction tracking | Capsule reducer ([ADR-030](./030-conversation-capsule.md)) |
| Permission escalation | Envelope authority is a ceiling, never a floor to climb |
| Final user-facing answer | One voice; workers return structured results |

### Candidates (implementation order)

| Worker | Job | Maps to |
| --- | --- | --- |
| **Evidence** (first) | Fresh private reads → ids, timestamps, grounded claims — **not prose** | `"ffs"` path · [C24](../../tickets/conversational-ui/C24-read-only-evidence-worker.md) |
| Decomposition | Compound request → individually satisfiable operations | later shape of [C19](../../tickets/conversational-ui/C19-multi-intent-decompose.md) |
| Explanation | Richer explain from **already-authorized** evidence | later; does not invent facts ([C21](../../tickets/conversational-ui/C21-grounded-values-no-invented-facts.md)) |
| Action verification | Inspect receipts only | later shape of [C17](../../tickets/conversational-ui/C17-execution-receipts-verification-ledger.md) / [ADR-032](./032-action-ledger-execution-receipts-verification.md) |
| External-world researcher | Cited public evidence; no unnecessary private context | later; lane 4 ([ADR-020](./020-llm-conversational-boundary-not-truth.md)) |

P0 ledger and attestation invariants land **without** workers. An action-verification worker must not exist until `action.inspect` and the claim fence already hold in the parent ([C17](../../tickets/conversational-ui/C17-execution-receipts-verification-ledger.md)).

### Envelope

Workers receive a deliberately small envelope. Authority on the envelope is a **ceiling** copied from the compiler. `APPROVE` / `EXECUTE` are never on a worker envelope.

```typescript
type SubtaskEnvelope = {
  objective: string
  authority: "NONE" | "READ" | "PROPOSE"
  allowedTools: ToolName[]
  evidenceIds: string[]
  privateContext?: MinimisedContext
  outputSchema: JsonSchema
  deadlineMs: number
}

type SubtaskResult = {
  status: "satisfied" | "partial" | "blocked"
  claims: GroundedClaim[]
  evidenceIds: string[]
  proposedOperations: Operation[]
  unresolved: string[]
}
```

`SubtaskResult.status` is worker-local completeness of **that task**. It is not capsule request satisfaction and not an execution receipt. The parent maps results into tools, ledger, and prose.

**No subagent may say “I sent it.”** Only the parent may translate a verified execution receipt ([ADR-032](./032-action-ledger-execution-receipts-verification.md)) into that claim.

### First path (`"ffs"`)

1. Capsule recovers the unresolved private request (question, not answer).
2. Compiler grants private **READ** (re-earn authority).
3. Parent dispatches a minimally scoped evidence envelope (`authority: READ`).
4. Worker returns fresh evidence ids/claims — not transcript residue.
5. Parent answers.

Bypassing the capsule or the compiler is a failed design.

## Consequences

- Do not claim [C24](../../tickets/conversational-ui/C24-read-only-evidence-worker.md) until P0 [C16](../../tickets/conversational-ui/C16-attested-completion-invalidates-next-action.md) + [C17](../../tickets/conversational-ui/C17-execution-receipts-verification-ledger.md) are `done`.
- Do not add conversational assistants. Do not give workers `recent_dialogue` as world truth.
- Related: [ADR-020](./020-llm-conversational-boundary-not-truth.md) · [ADR-029](./029-context-compilation-request-shaped-memory.md) · [ADR-030](./030-conversation-capsule.md) · [ADR-031](./031-semantic-bootstrap-compiler-grants-context.md) · [ADR-032](./032-action-ledger-execution-receipts-verification.md)

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Extra conversational personalities / polish LLM | Recreates authority leakage [ADR-020](./020-llm-conversational-boundary-not-truth.md) forbids |
| Workers decide referents, authority, or “I sent it” | Recreates the 61-turn confusion this sprint is engineering out |
| Stuff workers into `ConversationCapsule` | Capsule is frozen; workers consume `public_view()`, they do not live on it |
| Replace C17 with an action-verification personality | Invariant first; worker is later shape |
| OpenClaw-style broad operational reach | Enigma compiles what may be known and done before the model improvises |
