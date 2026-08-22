# Tone memory

**Status:** North Star — documentation only. No runtime.  
**Date:** 2026-08-17  
**Philosophy:** [north-star.md](./north-star.md) (squeeze 3 — lossy personal memory)  
**ADR:** [025 — Tone memory — how to speak, not who you are](../adr/025-tone-memory-how-to-speak-not-who-you-are.md)  
**Ticket:** [C11](../../tickets/conversational-ui/C11-tone-memory.md) (parked)  
**Depends (hard, before any implementation):** [C09 LLM proof](../../tickets/conversational-ui/C09-llm-conversational-boundary.md) (not harness-only)

> **Enigma may remember how to communicate with you without remembering the conversations that taught it how.**
>
> Store **style preferences**, not a personality dossier and not conversation logs.

## Why tone memory exists

C09's orchestrator should compose copy from **tool results + `current_subject`**, not from a rolling transcript. Users still want Enigma to sound like *their* Enigma: concise or not, casual or not, no productivity cheerleading.

That preference is a **small durable object**. It is not:

- the last 200 messages
- persistent-shadow world state ([ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md))
- Next Action category fitness ([N03](../../tickets/next-action/N03-preference-learning.md))
- a psychological profile

## Three layers

| Layer | Example | Durable? |
| --- | --- | --- |
| **USER-SET** | "Be concise." "Don't nag." | Yes — until the user changes it (`EXPLICIT_USER`, confidence `1.0`) |
| **LEARNED** | Repeatedly prefers light humour, options over instructions | Yes, weaker (`INFERRED`, e.g. confidence `0.65`); unreinforced decays |
| **TURN-LOCAL** | Frustrated *now*; wants a short answer *this turn* | **No** — evaporates. Never "user is irritable." |

```text
observation → temporary signal → repeated → candidate → stable tone memory → unreinforced decays
```

A single turn never graduates. Explicit correction skips the ladder.

## Coarse enums (closed set)

Dimensions only — illustrative values, not an implementation schema:

`directness` · `warmth` · `verbosity` · `humour` · `formality` · `encouragement` · `initiative` · `technical_depth` · `challenge_assumptions` · `avoid_productivity_cheerleading`

Store the **enum**, not the evidence. No `sarcasm_score: 0.73`, no profanity %, no affect embeddings.

```text
# explicit
verbosity = LOW          source = EXPLICIT_USER   confidence = 1.0

# learned
humour    = LIGHT        source = INFERRED        confidence = 0.65
```

## C09 payload (after proof)

Send a **small tone profile** with the current subject and tool results. Do **not** send conversation history as style memory.

```text
user message + tool schemas + current_subject + tool results + tone enums
        ↓
LLM chooses wording in that register
        ↓
Enigma still owns truth, policy, memory, execution ([ADR-020](../adr/020-llm-conversational-boundary-not-truth.md))
```

The model may use the profile. It may not write the dossier, invent world facts, or treat chat logs as durable identity.

**Tone may transform expression; it may not transform state, urgency, recommendation strength, or authority.** It rides on the C09 respond phase ([ADR-020](../adr/020-llm-conversational-boundary-not-truth.md)) — not a second personality LLM.

## Privacy

**`PRIVATE_DERIVED_PREFERENCE`** — subclass of `PRIVATE_DERIVED` ([ADR-022](../adr/022-private-vault-storage.md)):

- Less sensitive than raw conversation; still personal data
- Vault only; egress as coarse `REMOTE_SAFE` enums
- Inspectable: *"How do you think I like you to talk to me?"* → user corrects
- Forget and lineage apply ([data-retention.md](./data-retention.md))

## The line

| GOOD | BAD |
| --- | --- |
| Prefers concise, casual, options over instructions | Low self-esteem, emotionally avoidant, politically persuadable |
| Style enums the user can see and fix | Personality / political / medical inferences from how they talk |

Sensitive-inference ban still holds: do not accumulate inner-life labels from discourse ([data-retention.md — Sensitive inferences](./data-retention.md#sensitive-inferences-special-class)).

Persistent shadow answers *what still matters*. Tone memory answers *how to speak*. Neither is a biography. Secret personality profiling from discourse fails the [ethics creed](./ethics.md) ([ADR-026](../adr/026-ethics-creed-user-is-subject.md)): never secretly profile; inspect and correct.

## Sequencing

```text
C09 LLM proof  →  unpark C11
```

Do **not** implement now. Demo sketch after proof; Private vault persistence is a soft follow-on of SEC-01 / SEC-06. No external effects, so SEC-05 is not a hard gate for this object.

Until then: **capture ADR + this doc + C11, then stop.**

The alex-v1 six-month ordinary-events corpus ([demo-corpus.md](./demo-corpus.md#six-month-ordinary-life-d08f)) is the **fixture** for a real tone test (Jan signal → Feb repeat → Mar stable → Apr used → May/Jun decay). That does **not** unpark this ticket. D08f must not land a tone store.
