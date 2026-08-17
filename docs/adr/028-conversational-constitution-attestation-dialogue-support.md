# ADR-028: Conversational constitution — attestation, recent dialogue, support-before-Assist

**Status:** Accepted  
**Date:** 2026-08-17

> **If the user tells Enigma the world changed, conversation alone must never be the only place that change exists.**
>
> **Recent chat helps interpret. It does not establish world truth.**
>
> **Distress may increase supportiveness, never authority.**
>
> **Ambiguous help requests default to the least-authoritative useful interpretation.**

## Context

C09 made the LLM the conversational orchestrator ([ADR-020](./020-llm-conversational-boundary-not-truth.md)). Three product failures showed that interpretation without a constitution still leaks authority:

1. **Attestation.** Alex says “I've done the draft colours!” The model socially acknowledges, or calls `next_action.get`. The world stays OPEN. TOKEN remains the next action. The user reported a world change; conversation was the only place it existed.
2. **Recent dialogue.** After “I've finished it!” then “I'm excited to get going!”, the remote model sees only the current utterance plus structured state. It cannot interpret the follow-up. Sending the whole transcript would recreate a life.
3. **Help vs Assist.** “I need help with that” / “help, I'm overwhelmed” / “Yes help! I have ADHD…” were collapsing into `assist.propose` or `assist.approve`. Difficulty was silently raising what Enigma was allowed to do.

This ADR is the C09 constitution for those three memories. It does **not** expand `intent_router` phrase families.

## Decision

### Three memories

| Memory | What it is | What it is not |
| --- | --- | --- |
| **World state** | Durable facts. Tools establish truth. | Chat |
| **Conversation context** | Referents, focus, pending speech act | World truth, biography |
| **Recent dialogue** | 2–6 prior turns, egress-filtered | Transcript, tone memory, world evidence |

**Chat history remembers the conversation. World state remembers the world.**

Send enough previous conversation to understand meaning — not enough to recreate their life.

### User attestation

User **reports** are evidence. User **commands** grant authority.

- “I booked it” / “I've done the draft colours” → `world.record_user_attestation` (evidence `USER_ATTESTED` only)
- “Book it” / “Do the token inventory” → Assist (`assist.propose` then explicit `assist.approve`)

Recording a report does **not** require approval and does **not** mean external mutations. Conversation alone must never be the only place that change exists. USER_ATTESTATION must ACT (attest) before RESPOND. It is not Assist. `next_action.get` is not the primary action for a completion report.

Append-only attestations; a later row for the same `target_id` supersedes via `supersedes`. COMPLETED/CANCELLED leave the next-action projection (`completed_item_ids`). OPEN discards a prior completion. Discourse subject (`current_subject_id`) may stay on TOKEN; `current_next_action_id` must clear. Later-turn resurfacing of a completed task is [C16](../../tickets/conversational-ui/C16-attested-completion-invalidates-next-action.md): the overlay must invalidate cached next actions, not only the immediate `"What's next?"`.

### Bounded `recent_dialogue`

Shape: `{role, text|summary, act, subject_id}`. Cap: 6 turns (`RECENT_DIALOGUE_LIMIT`).

**Recent chat helps interpret the conversation. It does not establish world truth.**

Assistant turns that rendered local HIGH/private content must **not** be replayed raw to the hosted model (`egress_classification=local_only` + summary such as “Displayed a local quotation about the current subject”). User turns (their own words this session) generally send as text. Filter **before** `context_summary`; the privacy layer copies `recent_dialogue` onto the wire as a sibling of `user_message`.

### Support-before-Assist funnel

Never skip toward more authority:

```
UNDERSTAND
→ SUPPORT
→ PREPARE
→ PROPOSE
→ APPROVE
→ EXECUTE
```

**Distress may increase supportiveness, never authority.**

**Ambiguous help requests default to the least-authoritative useful interpretation.**

ADHD ethics: difficulty can change **how much friction Enigma removes**, but never **silently change what it is allowed to do**.

| Utterance | Landing | Tools |
| --- | --- | --- |
| `"help, I'm overwhelmed"` / `"I need help with that"` / `"I find this hard"` | SUPPORT | `world.explain` — discuss / explain / break down / first step. No propose, no approve, no execute. |
| `"can you draft something for me?"` | PREPARE | `assist.propose` — never skip to execute |
| `"do it"` / `"Can you help me do that?"` | PROPOSE then APPROVE | proposal + **explicit** approval ceremony, not silent execute |
| `"help!"` / `"heeeelllppp!!"` | ordinary social | no tool, no Assist |
| Distress + ADHD mention, even with a pending Assist | SUPPORT | never `assist.approve` |

`world.explain` on the SUPPORT path returns a useful payload (title, why, first step, support options, `assist_offered: false`) and prose that talks through the problem — not an Assist card.

The guard lives in Enigma core (`speech_acts` classifier, orchestrator constitution, `execute_tool` denials). Do not teach `intent_router` new English.

## Consequences

- Compromised or confused tool calls are rewritten or denied: SUPPORT cannot propose or approve; PREPARE cannot approve; ACTION_REQUEST cannot silently execute; USER_ATTESTATION cannot become Assist.
- Live Fireworks must still prove it *chooses* these tools. Constitution is the floor when it does not.
- Demo never shares Private storage roots. Frozen checkpoints are never mutated; attestation is a session overlay.
- Related: [ADR-020](./020-llm-conversational-boundary-not-truth.md) · [ADR-010](./010-next-action-not-attention.md) · [ADR-029](./029-context-compilation-request-shaped-memory.md) · [ADR-032](./032-action-ledger-execution-receipts-verification.md) · [ethics.md](../architecture/ethics.md) · [C09](../../tickets/conversational-ui/C09-llm-conversational-boundary.md)

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Expand `intent_router` help phrases | Frozen; C09 owns language. Constitution is speech-act + core guards. |
| Treat overwhelm as consent to Assist | Distress may increase supportiveness, never authority. |
| Send the full transcript remotely | Recreates a life. 2–6 egress-filtered turns is the cap. |
| Social acknowledgement of “I've done it” without a write | Conversation would be the only place the change exists. |
| Auto-approve on `"do it"` when a proposal is pending | Silent execute. Approval is an explicit ceremony (`Go on then.`). |
