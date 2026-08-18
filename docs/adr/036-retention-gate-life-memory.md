# ADR-036: Retention gate separates establishment from life memory

**Status:** Accepted  
**Date:** 2026-08-18

> **Truth does not imply retention.**
>
> **Confirmation grants epistemic status. Purpose grants retention.**

## Context

The conversational stack now has frozen layers for:

- grounded truth ([ADR-035](./035-grounded-assertions-and-evidence-pack.md) · C26)
- response grounding (C26 bridge)
- continuity (C27)
- event/work spine (C28)

[SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md) already implements **storage-plane** retention: lineage metadata, decay, forget cascades, and sensitive-inference write guards on `DerivedRecord` rows in the encrypted vault.

What is still missing is the **semantic gate** that answers, for each `GroundedAssertion`:

> Given this proposition is established strongly enough to reason with, is it **justified** to survive beyond the work that produced it?

`GroundedAssertion.retention_class` on the evidence plane is a **hint**, not a decision. C29 introduces an explicit `RetentionDecision` produced by `evaluate_retention()` before any durable write.

## Decision

### 1. Retention gate sits between grounding and storage

```text
GroundedAssertion (ephemeral evidence plane)
  → evaluate_retention()
  → RetentionDecision (DURABLE | TTL | EPHEMERAL | REJECT)
  → DurableAssertionStore (small life-memory slice)
  → SEC-06 DerivedRecord lineage (existing vault semantics)
```

Establishment (epistemic status, evidence refs) and retention (purpose, lifetime, proportionality) are **separate pipelines**.

### 2. Scope is seven items only

C29 owns:

1. retention decision
2. retention class / lifetime
3. retention purpose
4. provenance preservation
5. third-party restrictions
6. correction / deletion (gate + stub store; SEC-06 owns vault cascade)
7. derivative invalidation (stub lineage; SEC-06 owns production cascade)

### 3. First memory model — boring and practical

Retain only concrete life facts: people, relationships, projects, commitments, dates, birthdays, plans, preferences, gift history, places, dependencies, shared conventions.

Explicitly **not** in scope: personality vectors, relationship strength scores, inferred psychology, giant ontology.

### 4. Third-party ethics

Third-party retention is limited to **concrete, user-owned purposes** (e.g. "Maya likes ceramics" for gift planning). Psychological, behavioural, or relational profiling predicates are **rejected** at the gate unless extraordinary explicit product justification exists (none in v0).

### 5. Life Graph and Goose are downstream projections

- **Life Graph** (C30 Brain projection) compiles from retained assertions — it does not decide retention.
- **THE Goose** is presentation-only ([ADR-035](./035-grounded-assertions-and-evidence-pack.md)); it may retrieve facts for display but **never** decides what gets remembered.

### 6. Build on SEC-06, do not duplicate

| Concern | Owner |
| --- | --- |
| `RetentionDecision` / `evaluate_retention()` | C29 · `packages/domain/retention_gate.py` |
| `DerivedRecord` lineage, decay, forget graph | SEC-06 · `apps/api/storage/` |
| Sensitive inference permanent-write ban | SEC-06 · `storage/sensitive.py` |
| Durable life-memory assertion store | C29 slice 2+ (stub in slice 1) |

When a C29 decision is `DURABLE` or `TTL`, a later slice maps it to `DerivedRecord` + `LineageMetadata` using existing SEC-06 fields — no parallel forget graph.

Slice 3 forgetting is **semantic invalidation**: delete unjustified `derived_records` rows and strip forgotten lineage refs from survivors. It is not cryptographic destruction of SQLCipher pages. Residual ciphertext after `DELETE` is a later storage-hardening concern; freeze readiness at this layer is that forgotten content cannot participate in current memory.

## Implementation dependency order

```text
RetentionPolicy / RetentionDecision  ← slice 1 (this ADR)
  ↓
small durable assertion store
  ↓
deletion + derivative invalidation (wire to SEC-06 forget)
  ↓
only then richer Life Graph projections (C30)
```

## Consequences

- `packages/domain/retention_gate.py` is the canonical retention decision function.
- Evidence packs and respond grounding remain ephemeral; they do not write durable memory.
- Freeze tests (Ceramics, Detective, Forget, Third-party, Purpose-expiry) gate future Life Graph work.
- C30 Brain projection must compile from `DurableAssertionStore` + SEC-06 inventory, not invent parallel truth.

## Non-goals

- Not reopening C26 grounding, respond_grounding, C27 continuity, or C28 event spine.
- Not a general ontology or psychographic model.
- Not Goose memory UI.
- Not permission for the LLM to write durable memory directly.

## Related

- [data-retention.md](../architecture/data-retention.md)
- [ADR-035](./035-grounded-assertions-and-evidence-pack.md)
- [ADR-023](./023-persistent-shadow-abstract-state-not-biography.md)
- [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md)
- [C29](../../tickets/conversational-ui/C29-life-memory-and-retention.md)
