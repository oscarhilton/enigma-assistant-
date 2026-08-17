# ADR-029: Context compilation — request-shaped memory, not prompt pruning

**Status:** Accepted  
**Date:** 2026-08-17

> **World state is truth — not chat history.**
>
> **Conversation state resolves language; tools establish truth.**
>
> **Context may help the model understand the question. It may not answer the question.**
>
> **The request chooses the context.** / **The request selects what to fetch, transform, and send.**
>
> **Long memory underneath. Short attention above.**
>
> **Words are working memory. State is memory.**
>
> **Every piece of remote context must have a request-derived justification. No justification → compiler doesn't fetch it.**
>
> **Context that is not required for this request does not enter the prompt.**
>
> **Once conversation has safely changed structured state, the words that caused the change should usually become disposable.**

## Context

C09 made the hosted model the conversational orchestrator ([ADR-020](./020-llm-conversational-boundary-not-truth.md)). [ADR-028](./028-conversational-constitution-attestation-dialogue-support.md) froze three memories: world writes for user reports, bounded recent dialogue, support-before-Assist.

That still left a load-then-redact habit: assemble a universal envelope, attach the full tool registry, hope the model focuses. Select-first ([privacy-model.md](../architecture/privacy-model.md)) was the product rule; the orchestrator was not compiling to it.

This ADR freezes **context compilation** as core Enigma memory architecture — not C09 prompt-engineering notes.

## Decision

### Compiler, not pruner

```text
USER REQUEST
    ↓
INTERPRET REQUEST PROFILE
    ↓
CONTEXT REQUIREMENTS
    ↓
FETCH only permitted/relevant state
    ↓
TRANSFORM for this purpose
    ↓
COMPILE minimal model context
    ↓
LLM
```

Not: load everything → redact some things → hope the model focuses.

Internal names: `compile_remote_context` / context compilation. Not `prune_prompt`.

### Request profiles

Profiles are authority / evidence regimes, not classic intents and not English routing. INTERPRET locally: evidence domain, then authority, then **candidate capability families**. Profile does not pick the exact tool before families are visible.

**Context compilation should remove irrelevant knowledge, not remove Enigma.**

Orthogonal dimensions:

| Dimension | Values |
| --- | --- |
| `evidence_domain` | `PRIVATE_WORLD` · `GENERAL_KNOWLEDGE` · `EXTERNAL_WORLD` · `CONVERSATION_ONLY` |
| `authority` | `NONE` · `READ` · `SUPPORT` · `ATTEST` · `PREPARE` · `APPROVE` · `EXECUTE` |

Do not: classify → profile → profile determines exact tools.
Do: interpret → infer evidence domain → infer authority → compile profile + candidate families + context requirements.

`GENERAL_KNOWLEDGE` must not swallow questions that are syntactically questions but epistemically private. `"What's on this week?"` is `PRIVATE_WORLD` / `READ` / `agenda.get`, not sky trivia. `"What about at work?"` inherits `this_week` and adds `scope=work`. Conversational wrapping (`"I want to know what I should be focused on right now"`) stays private SUPPORT + attention — it is not ordinary chat.

Recall before precision: first recognize “this needs private truth,” then minimise which private context. The compiled tool surface may hide irrelevant capabilities. It must **not** hide the capability required to satisfy the request (compiler-induced capability lie).

### Objective function

This is the compiler’s score, not a new `intent_router`. Frozen phrase families stay frozen.

| Number | Target |
| --- | --- |
| Recall of required capabilities | **HIGH** |
| Irrelevant private context | **LOW** |
| Authority escalation | **ZERO** |

**Never prune away the capability needed to answer. Never include private context merely because it might help.**

Catastrophic false negatives (private questions compiled as sky trivia) come first. Once those are closed, do not swing to over-classification toward `PRIVATE_WORLD`. Conversational and general questions (`wait`, `:)` , “What is OAuth?”, “how do design tokens work?”, “whats the colour of the sky”) must not drag agenda / attention / `assist.approve` in “just in case.” Bare `"yes"` with no live `APPROVE_CONFIRMATION` must not compile `EXECUTE` / `assist.approve`.

Wire profile names stay the authority/evidence regime for egress:

| Profile | Domain + authority | Remote context | Tools |
| --- | --- | --- | --- |
| `CONVERSATION` | `CONVERSATION_ONLY` / `NONE` | Working-set anaphora | none |
| `GENERAL_KNOWLEDGE` | `GENERAL_KNOWLEDGE` / `NONE` | **none** | **none** |
| `PRIVATE_QUERY` | `PRIVATE_WORLD` / `READ` | Subject, attention working set, clock, recent dialogue | query tools (agenda / attention / availability) |
| `SUPPORT` | `PRIVATE_WORLD` / `SUPPORT` | Subject + support summary + attention | `world.explain`, `attention.get_current` (no Assist) |
| `USER_ATTESTATION` | `PRIVATE_WORLD` / `ATTEST` | Subject + named referents | `world.record_user_attestation` only |
| `PREPARE_ACTION` | `PRIVATE_WORLD` / `PREPARE` | Subject + pending Assist id | `assist.propose` |
| `AUTHORITATIVE_ACTION` | `PRIVATE_WORLD` / `APPROVE` | Subject + pending Assist id | `assist.propose`, `assist.approve` |

Only **live** discourse state is compiled. `pending_dialogue_act` carries `created_turn` / `consumed_by` / `expires_after_turns`. Stale `SHOW_CONFIRMATION` and `focus_reason=empty_horizon` with no live SHOW exchange do not enter the remote prompt.

`intent_router` phrase families stay frozen.

### Compiled-turn manifest

A compiled turn has a typed manifest the privacy audit can use — not merely what was excluded, but **why each included context earned its place**.

Shape (`packages/privacy/.../egress/disclosure.py`):

```text
profile: private_query
speech_act: QUESTION

context:
  recent_dialogue:
    include: true
    max_turns: 6
    remote_safe_only: true
    justification: Chat history explains meaning; it does not become world truth.
  current_subject:
    include: true
    justification: Conversation state resolves language; tools establish truth.
  attention:
    include: true
    justification: This private-world query earned the current projection.
  calendar:
    include: false
    justification: No request-derived justification. …
  source_raw:
    include: false
    justification: Raw sources never enter the remote prompt.

tools:
  - attention.get_current
  - next_action.get
excluded_tools:
  - assist.approve
  - …
```

The manifest lives on `EgressDisclosure.context_manifest` and Cortex membrane events. It is **not** stuffed into the LLM user message. Justifications are for the privacy audit.

### Attestation as compilation allowing text to die

`"I finished the token draft"` → `USER_ATTESTATION(TOKEN, COMPLETED)` → world write → attention rederived → the literal utterance is no longer required.

The sentence was temporary computation. The resulting state is durable because it has a defined purpose. After the write, TOKEN’s absence from next-action is overlay (`completed_item_ids`), not chat.

### Six-month / SEC-07 (docs, not D08f authoring)

By June 30:

- **PROMPT CONTINUITY** Jan–Jun: almost none
- **WORLD CONTINUITY** Jan–Jun: selectively preserved

“What happened with that thing I was waiting on?” is answerable because the world transition survived, not because Fireworks gets six months of transcripts.

“What exact words did Maya use in February?” may be impossible because the raw source expired. **That is not memory failure. That is successful forgetting.**

[D08f](../../tickets/demo-scenario/D08f-alex-six-month.md) can eventually test three independent curves (do not author the corpus here):

```text
                 time →
raw recoverability     ███████▃▁
dialogue recoverability████▂▁▁▁
world utility          █████████
```

[SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) measures: biographical reconstruction ↓ while executive-function utility remains ↑.

Context compilation is the mechanism connecting the conversational side to that privacy model.

## Consequences

- `run_orchestrator_turn` compiles before the planner. Fireworks sees the earned working set and the earned tools. Scripted / compromised planners may still *request* other tools; constitution + `execute_tool` remain the floor.
- `GENERAL_KNOWLEDGE` transmits no private modules and no tools. It is not the default for every `?`.
- Conversational / generic turns (`wait`, `:)` , “What is OAuth?”) stay `CONVERSATION` / `GENERAL_KNOWLEDGE`. Bare `"yes"` without live `APPROVE_CONFIRMATION` does not compile `assist.approve`.
- `SUPPORT` cannot see `assist.approve` on the wire. It can see `attention.get_current` when the request is about focus.
- Horizon constraints inherit across follow-ups (`this_week` survives `"What about at work?"`).
- `SUPPORT` cannot see `assist.approve` on the wire.
- Local `context_summary()` remains the full session view for tests and oracle follow-ups (`last_intent_kind` is local-only; it is stripped from the remote user payload).
- Related: [ADR-020](./020-llm-conversational-boundary-not-truth.md) · [ADR-028](./028-conversational-constitution-attestation-dialogue-support.md) · [conversational-stream.md](../architecture/conversational-stream.md) · [privacy-model.md](../architecture/privacy-model.md) · [data-retention.md](../architecture/data-retention.md) · [demo-corpus.md](../architecture/demo-corpus.md#six-month-ordinary-life-d08f)

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Load everything, redact, hope | Inverse of select-first; no request-derived justification |
| Prompt-pruning until the window fits | Size is not the criterion; unearned context must not enter |
| Full tool registry every turn | Authority leakage; SUPPORT must not see approve |
| Put the manifest in the user message | Audit object; stuffing justifications teaches the model to recite policy |
| Keep six months of transcripts for “memory” | Prompt continuity is the reconstructability leak SEC-07 exists to fail |
