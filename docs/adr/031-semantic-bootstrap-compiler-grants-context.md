# ADR-031: Semantic bootstrap interprets; the compiler grants context

**Status:** Accepted  
**Date:** 2026-08-17

> **The semantic model interprets the request. The compiler grants context.**

```text
The capsule carries continuity.
The bootstrap interprets language.
The compiler grants context.
The world establishes truth.
```

The bootstrap may improve comprehension. It may not improve its own authority.

## Context

[ADR-030](./030-conversation-capsule.md) froze the conversation capsule: inherit evidence and constraints, re-earn authority, distinguish request satisfaction from a decaying frame. [ADR-029](./029-context-compilation-request-shaped-memory.md) `interpret_request()` is the **deterministic baseline**: obvious cases, tests, and the safe fallback.

The remaining problem is different: how Enigma understands natural, elliptical language well enough to *feed* the compiler without turning the compiler into an English phrasebook.

Fresh `"anything coming up?"` is epistemically private, but the compiler correctly refuses a regex family for it. `"what about work?"` should add `scope=work` from discourse + language, not from `"at work" | "for work"` catalogues in `interpret_request`.

The bootstrap paradox: you need a rough meaning before deciding which private material the main model may see — without encoding all meanings as regexes, and without giving the interpreter Alex's private world.

## Decision

An optional layer sits *in front of* the ADR-029 compiler. Capsule continuity is ADR-030. This ADR is only the bootstrap interpreter.

```text
NEW UTTERANCE
      +
CONVERSATION CAPSULE
      ↓
SEMANTIC BOOTSTRAP
(no private-world context)
      ↓
RequestInterpretation
      ↓
DETERMINISTIC CONTEXT/AUTHORITY COMPILER
      ↓
fetch → transform → capability fence
      ↓
MAIN LLM / tools
      ↓
response
      ↓
UPDATE CAPSULE
      ↺
```

`interpret_request()` stays the deterministic/compiler-side interpretation baseline. Candidate families from bootstrap are **suggestions**. The compiler still does `families ∪ profile floor ∩ authority fence ∩ capability policy`.

### Semantic bootstrap

The bootstrap model does **not** receive Alex's private world. It receives:

```json
{
  "utterance": "anything coming up?",
  "conversation": {
    "active_goal": null,
    "temporal_frame": null,
    "scope": null,
    "source_scope": null,
    "unresolved_request": null
  }
}
```

and returns a constrained interpretation (domain, authority, candidate families, temporal/scope hints, inherit flag, confidence). Enigma — not that model — decides which tools exist and which private context can be fetched.

The payload is `assert_remote_safe` (`semantic_bootstrap_v1`). No obligations, no names, no attention items, no source bodies, no tool schemas. Reuse `RemoteSafeContext` / `TransformedContext` egress machinery.

Live Fireworks bootstrap is optional and behind `ENIGMA_SEMANTIC_BOOTSTRAP`. Unit tests use a typed `SemanticBootstrap` protocol with a **fixture oracle**. They must not require `FIREWORKS_API_KEY`.

### Conservative merge

```text
deterministic interpretation
        +
semantic interpretation
        +
conversation capsule
        ↓
merge conservatively
        ↓
compiler
```

**The semantic layer cannot increase authority casually.** Capsule `previous_authority` is not a grant.

```text
NONE < READ < SUPPORT < ATTEST/PREPARE < APPROVE < EXECUTE
```

Prefer `min(authority)` / the safer of the two. `ATTEST`/`PREPARE`/`APPROVE`/`EXECUTE` require **explicit evidence** that the deterministic side already recognizes. Example: deterministic `SUPPORT` + semantic `APPROVE` ≠ `APPROVE`.

When semantic (or capsule inheritance) promotes `GENERAL_KNOWLEDGE` → `PRIVATE_WORLD` for an elliptical private question, `NONE` lifts to `READ`. That is the minimum useful private-query authority. It is not a path to Assist.

Evidence domain: semantic **may** add `PRIVATE_WORLD` when deterministic said `GENERAL_KNOWLEDGE` for elliptical private questions (`"anything coming up?"`). Semantic **must not** invent `PRIVATE_WORLD` for `"why is rain wet?"` / `"why is the sky blue?"`. Merge refuses domain promotion when the compiler already classified the utterance as generic public-world knowledge.

`EXTERNAL_WORLD` stays dormant. Do not infer a lane that cannot be satisfied; treat it as `GENERAL_KNOWLEDGE`.

## Consequences

- `"anything coming up?"` via semantic(+capsule) compiles `PRIVATE_WORLD` / `READ` / agenda. The same utterance without bootstrap remains the deterministic `GENERAL_KNOWLEDGE` baseline — that is not a compiler bug.
- `"What's on this week?"` then `"what about work?"` inherits `this_week` from the ADR-030 frame and adds `scope=work` from bootstrap, not from `_WORK_SCOPE`.
- `"and?"` / `"what else?"` inherit the live capsule frame (ADR-030 deterministic inherit, plus bootstrap `inherit_capsule`).
- Profile floors stay fat for now (`PRIVATE_QUERY` still includes attention + blockers + explain alongside agenda). Shrinking floors so `families=["agenda"]` yields only `agenda.get` is later-safe and must not reintroduce `"I wish I could read your calendar"`.
- `intent_router` English catalogues stay frozen. Do not start D08f corpus authoring here.
- Related: [ADR-030](./030-conversation-capsule.md) · [ADR-029](./029-context-compilation-request-shaped-memory.md) · [ADR-020](./020-llm-conversational-boundary-not-truth.md) · [C15](../../tickets/conversational-ui/C15-semantic-bootstrap-capsule.md) · [conversational-stream.md](../architecture/conversational-stream.md)

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Add `"anything coming up?"` regexes to `interpret_request` | Compiler becomes an English phrasebook; C09 freeze |
| Stuff this into ADR-029 or ADR-030 | Different problem: ADR-029 grants context; ADR-030 carries continuity; this layer interprets language |
| Give the bootstrap model attention / obligations / names | Bootstrap paradox solved by leaking the world; violates select-first |
| Let semantic `APPROVE` win when the model is confident | Authority escalation; constitution forbids it |
| Inherit capsule `previous_authority` as a grant | ADR-030: authority must be re-earned |
| Require Fireworks for unit tests | CI must prove the merge without a hosted model |
| Infer `EXTERNAL_WORLD` for news/weather | Lane cannot be satisfied; dormant until a real external capability exists |
