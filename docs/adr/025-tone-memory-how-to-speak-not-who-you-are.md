# ADR-025: Tone memory — how to speak, not who you are

**Status:** Accepted  
**Date:** 2026-08-17

> **Enigma may remember how to communicate with you without remembering the conversations that taught it how.**
>
> Store **style preferences**, not a personality dossier and not conversation logs.

## Context

[ADR-020](./020-llm-conversational-boundary-not-truth.md) splits conversational labour: the LLM interprets and composes; Enigma holds truth, policy, memory, and execution. C09's intended remote payload is the current utterance, tool schemas, `current_subject`, and tool results — **not** a rolling transcript.

Without a named object for *how to speak*, two failure modes compete:

1. **Transcript-as-memory** — send the last 200 messages so the model "sounds like us." That re-introduces conversation logs as durable context, enlarges remote view, and treats chat history as a personality archive.
2. **Psychological profiling** — infer who the user *is* (self-esteem, avoidance, persuadability) from how they talked once. That violates the [sensitive-inference ban](../architecture/data-retention.md#sensitive-inferences-special-class) and [ADR-023](./023-persistent-shadow-abstract-state-not-biography.md)'s reconstructability budget: Enigma must be a poor biography, including of inner life.

[N03](../../tickets/next-action/N03-preference-learning.md) already parks a different preference: Next Action *category fitness* from accept/reject — not communication style. [ADR-011](./011-observable-support-challenges-only.md) forbids diagnostic labels on the person record. C09's out-of-scope line ("productivity coach tone / durable user traits from rejection") is this gap, not permission to skip it.

The missing object is **tone memory**: a small, inspectable, decaying profile of *how Enigma should talk*, derived from explicit instruction and repeated interaction — never from a single frustrated turn, never as a psych dossier.

This ADR is the North Star. It does **not** authorise a tone store, learner, or C09 payload change. Those wait on [C09 LLM proof](../../tickets/conversational-ui/C09-llm-conversational-boundary.md) (not harness-only). See [tone-memory.md](../architecture/tone-memory.md) and [C11](../../tickets/conversational-ui/C11-tone-memory.md).

## Decision

### Core line

**Tone memory stores how to speak, not who you are.**

Enigma may retain coarse communication-style preferences. It must not retain conversation logs as style evidence, and must not accumulate psychological or political profiles from discourse.

### Three layers

| Layer | What it is | Lifetime | Confidence |
| --- | --- | --- | --- |
| **USER-SET TONE** | Explicit instruction ("Be concise", "Don't nag") | Durable until the user changes it | `1.0` — source `EXPLICIT_USER` |
| **LEARNED TONE** | Stable patterns from *repeated* interaction | Durable but weaker; unreinforced decays | `< 1.0` — source `INFERRED` |
| **TURN-LOCAL TONE** | This turn only (frustrated now, wants a quick answer) | **Evaporates** with the turn | Never promoted from one observation |

Turn-local must never become "user is irritable." Frustration, brevity-this-once, or a sharp correction is a **session signal**, not a person trait.

The same evaporate rule applies to **turn-local world constraints** (“we will be in Shoreditch” → `{location=Shoreditch, applies_to=Saturday brunch}`). They are not durable user memory and not an action ([ADR-020](./020-llm-conversational-boundary-not-truth.md) five lanes).

### Coarse enums only

Durable tone is a **small closed set of dimensions**, each an enum (or boolean constraint) — not a continuous psychometrics vector.

| Dimension | Role (illustrative values, not a frozen schema) |
| --- | --- |
| `directness` | `DIRECT` · `BALANCED` · `SOFT` |
| `warmth` | `COOL` · `NEUTRAL` · `WARM` |
| `verbosity` | `LOW` · `MEDIUM` · `HIGH` |
| `humour` | `NONE` · `LIGHT` · `PLAYFUL` |
| `formality` | `CASUAL` · `NEUTRAL` · `FORMAL` |
| `encouragement` | `MINIMAL` · `MODERATE` · `HIGH` |
| `initiative` | `WAIT` · `SUGGEST` · `PUSH` |
| `technical_depth` | `PLAIN` · `MIXED` · `TECHNICAL` |
| `challenge_assumptions` | `RARELY` · `SOMETIMES` · `OFTEN` |
| `avoid_productivity_cheerleading` | `ON` · `OFF` |

**Forbidden as stored evidence:** `sarcasm_score: 0.73`, profanity percentage, affect time-series, embedding-of-the-user, free-text personality summaries. Derived *answers* (the enum) are what persist; the conversational evidence that produced them does not.

Same derived-answer discipline as [ADR-023](./023-persistent-shadow-abstract-state-not-biography.md) / NIST Control-P: prefer the coarse property over the underlying transcript.

### Decay + correction

Learned tone follows a promotion ladder. One observation is not a preference.

```text
observation
    → temporary signal          (turn-local; discarded)
    → repeated observations
    → candidate
    → stable tone memory        (INFERRED, confidence < 1.0)
    → unreinforced decays
```

Explicit user correction **wins immediately** and does not wait for the ladder:

```text
verbosity = LOW
source    = EXPLICIT_USER
confidence = 1.0
```

Learned example (never as confident as an instruction):

```text
humour    = LIGHT
source    = INFERRED
confidence = 0.65
```

Unreinforced inferred dimensions decay back toward unset / default. Explicit dimensions persist until the user revises them. Forget of a conversation that *taught* a learned dimension must not be required to keep the enum — the transcript is not the store.

### C09 composition (after proof, not now)

When the conversational orchestrator is live, the remote model receives a **small REMOTE_SAFE tone profile** together with `current_subject` and tool results — **instead of** the last 200 messages.

```text
USER MESSAGE
    + tool schemas
    + current_subject (structured)
    + tool results
    + tone profile (coarse enums only)
        ↓
LLM composes copy in that register
        ↓
Enigma still owns truth, policy, memory, execution
```

The LLM may *use* the profile to choose wording. It may **not** invent world facts, rewrite tone memory, or treat chat history as durable style evidence. Updating learned tone is an Enigma-core job after the turn, from structured signals — not from the model writing a dossier.

**Tone may transform expression; it may not transform state, urgency, recommendation strength, or authority.**

```
WORLD TRUTH ───────────┐
                      ↓
CURRENT CONVERSATION → C09 RESPOND (same conversational boundary)
                      ↑
TONE PROFILE ─────────┘
```

A polish model that upgrades `urgency: LOW` into “you should probably do this today” has left the tone object and entered authority. That is forbidden.

### Privacy class

**`PRIVATE_DERIVED_PREFERENCE`** — a **purpose-scoped subclass of `PRIVATE_DERIVED`**, not a new egress class and not a sixth ADR-022 column.

| Property | Rule |
| --- | --- |
| Sensitivity | Less sensitive than raw conversation (`PRIVATE_RAW` transcripts) — still **personal data** |
| At-rest | Encrypted vault only ([ADR-022](./022-private-vault-storage.md)) |
| Egress | Never as-is; project coarse enums → `REMOTE_SAFE` for C09 |
| Inspectable | User can ask *"How do you think I like you to talk to me?"* and correct the answer |
| Forget | User correction and forget cascade apply; inferred rows carry lineage |

Pseudonymised preference data remains personal data while Enigma can attach it to the user ([data-retention.md — Regulatory alignment](../architecture/data-retention.md#regulatory-alignment-brief)).

### The line

| GOOD (style) | BAD (dossier) |
| --- | --- |
| Prefers concise, casual, options over instructions | Low self-esteem |
| `verbosity=LOW`, `formality=CASUAL`, `initiative=SUGGEST` | Emotionally avoidant |
| `avoid_productivity_cheerleading=ON` | Politically persuadable |
| "Don't nag" → `encouragement=MINIMAL` | Medical, sexual, financial, or political inferences from tone |

Do **not** accumulate psychological profiling. Align with the [sensitive-inference ban](../architecture/data-retention.md#sensitive-inferences-special-class): medical/health, sexuality, political affiliation, substance use, intimate relationships, financial distress, behavioural routines — and the same spirit for personality / persuadability labels. Temporary relevance for *this turn's* wording is TURN-LOCAL. Permanent "who you are" memory is out.

Persistent shadow ([ADR-023](./023-persistent-shadow-abstract-state-not-biography.md)) remains an index of *what still matters* in the world. Tone memory is a sibling object: *how to speak*. Neither layer stores biography of character.

## Sequencing (hard)

Do **not** implement a tone store, learner, or C09 payload field now.

| Prerequisite | Why |
| --- | --- |
| [C09](../../tickets/conversational-ui/C09-llm-conversational-boundary.md) **LLM proof** (not harness-only) | Tone profile is only useful once the orchestrator actually composes from tools; regex `intent_router` does not need it |

Private vault persistence additionally wants [SEC-01](../../tickets/security/SEC-01-secrets-encrypted-storage.md) / [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md) for classification and decay — **soft** for a Demo-only sketch after C09 proof. Do not block the North Star on SEC-05; tone memory has no external effects.

Parked ticket: [C11](../../tickets/conversational-ui/C11-tone-memory.md).

## Consequences

- C09 stays a tool-calling proof; it does not grow transcript memory or a coach persona.
- Future orchestrator context is **small and structured**: subject + tools + tone enums — not chat-log RAG.
- Inspect/correct ("how do you think I like you to talk?") is a first-class privacy surface, sibling to *"What do you remember about me?"*
- Agents must not land psychometrics, sarcasm scores, conversation-log retention-as-style, or "user is irritable" traits under C09, N03, or SEC tickets.
- N03 remains Next Action category fitness; it must not absorb communication style.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Last-N conversation messages as style memory | Enlarges remote view; treats logs as durable identity; fails reconstructability |
| Continuous scores (`sarcasm_score`, profanity %) | Fake precision; evidence-shaped; hard to inspect or correct |
| Personality / DSM-flavoured traits | Sensitive inference; ADR-011 / ADR-023 violation |
| One frustrated turn → durable "irritable" | TURN-LOCAL must evaporate |
| LLM writes the dossier each turn | Authority leak; model is not memory ([ADR-020](./020-llm-conversational-boundary-not-truth.md)) |
| Fold into N03 reject-learning | Different object (task fitness vs how to speak) |
| Fold into persistent-shadow obligation rows | Shadow is world state, not register |

## Related

- [north-star.md](../architecture/north-star.md) — lossy personal memory; consequence, not experience
- [tone-memory.md](../architecture/tone-memory.md) · [C11](../../tickets/conversational-ui/C11-tone-memory.md)
- [ADR-020](./020-llm-conversational-boundary-not-truth.md) · [C09](../../tickets/conversational-ui/C09-llm-conversational-boundary.md)
- [ADR-023](./023-persistent-shadow-abstract-state-not-biography.md) — abstract state, not biography
- [ADR-022](./022-private-vault-storage.md) — vault classification; this is a `PRIVATE_DERIVED` subclass, not a new egress class
- [data-retention.md — Sensitive inferences](../architecture/data-retention.md#sensitive-inferences-special-class)
- [ADR-011](./011-observable-support-challenges-only.md)
- [N03](../../tickets/next-action/N03-preference-learning.md) — Next Action fitness, not tone
- [ADR-026](./026-ethics-creed-user-is-subject.md) · [ethics.md](../architecture/ethics.md) — style enums are inspectable; inner-life profiling is forbidden
- [ADR-038](./038-humour-constitution-not-user-trainable.md) — humour constitution sits below personalisation; not a trainable taste dossier
