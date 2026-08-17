# ADR-035: Grounded assertions and ephemeral evidence packs

**Status:** Accepted  
**Date:** 2026-08-18

> **Inference may create a question. Evidence may create a fact.**
>
> **Truth does not imply retention.**
>
> **The model receives breadth of meaning, not breadth of source material.**

## Context

The repo already has several correct seams:

- [ADR-029](./029-context-compilation-request-shaped-memory.md) says requests choose context and compiled turns are minimal.
- [ADR-030](./030-conversation-capsule.md) keeps conversational continuity separate from world truth.
- [ADR-034](./034-evidence-coverage-bundle.md) adds a typed bundle for what was searched and whether coverage is adequate.
- `packages/domain` already contains retention lineage primitives used by SEC-06 forget flows.

What is still weak is the semantic unit between raw/tool evidence and model reasoning. Current `EvidenceBundle` answers **where Enigma looked** and **whether the search was sufficient**, but it does not yet make proposition-shaped knowledge first-class enough to answer:

- what exactly do I know?
- how do I know it?
- what merely seems plausible?
- what is missing, stale, or conflicted?
- what evidence would change the answer?

## Decision

Introduce a canonical proposition substrate in `packages/domain` and use it as the first foundation slice for evidence reasoning:

### 1. Grounded assertions

Add `GroundedAssertion` with:

- proposition shape: `subject`, `predicate`, `value`
- epistemic class: `EpistemicStatus`
- provenance: `evidence_refs`, `derived_from`
- time: `observed_at`, `valid_from`, `valid_until`
- governance: `sensitivity`, `retention_class`, `egress_class`
- promotion boundary: `AssertionKind`

This is the minimum inspectable unit for “what Enigma currently treats as grounded enough to reason with”.

### 2. Epistemic classes survive confidence

Confidence is optional metadata. It never promotes epistemic class.

`MODEL_INFERRED confidence=0.99` is still not equivalent to `SYSTEM_VERIFIED` or `EXTERNALLY_VERIFIED`.

### 3. Evidence packs remain ephemeral

Request-shaped evidence packs / bundles are compiled from:

```text
current request
+ retained assertions
+ freshness / privacy / authority filters
-> EvidencePack
-> model
-> discard
```

Compiled context is not a durable archive of everything Enigma considered relevant at a moment in time.

### 4. Unknowns and challenge semantics are first-class

The evidence plane must also carry:

- `EvidenceUnknown` for missing evidence, unavailable capability, unresolved referent, stale state, or conflict
- `AssertionChallenge` for whether a material premise is confirmed, qualified, contradicted, or not yet addressed

This keeps “bank holiday found” distinct from “therefore user is not working”.

### 5. Goose remains presentation only

Any Goose rendering is downstream of this substrate. It may visualise agent work and evidence state; it may not determine truth, tool choice, retries, scheduling, escalation, interruption, or retention.

## Consequences

- `packages/domain` becomes the canonical home for proposition-shaped grounding models.
- `EvidenceBundle` may carry grounded assertions, unknowns, and challenges without becoming durable memory.
- Later Brain/Cortex/Case projections should prefer compiling from these primitives rather than inventing parallel truth stores.
- Shared-culture or product-language concepts must not appear in these domain models.

## Non-goals

- Not a general ontology.
- Not permission for the LLM to write durable memory directly.
- Not a complete life graph.
- Not a second world model beside existing authoritative state.
