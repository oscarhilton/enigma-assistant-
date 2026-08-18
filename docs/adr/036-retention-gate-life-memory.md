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
| Durable life-memory assertion store | C29 slice 2+ |
| `MemoryInventory` projection | C29 slice 4 · `packages/domain/memory_inventory.py` |

When a C29 decision is `DURABLE` or `TTL`, it maps to `DerivedRecord` + `LineageMetadata` using existing SEC-06 fields — no parallel forget graph.

Slice 3 forgetting is **semantic invalidation**: delete unjustified `derived_records` rows and strip forgotten lineage refs from survivors. It is not cryptographic destruction of SQLCipher pages. Residual ciphertext after `DELETE` is a later storage-hardening concern; freeze readiness at this layer is that forgotten content cannot participate in current memory.

### 7. Memory inventory is a projection, not a store (slice 4)

```text
retained assertions (vault)
      ↓
MemoryInventory projection
      ↓
KNOWN | POSSIBLE | STALE | CONFLICTED | EXPIRING
```

`MemoryInventory` (`packages/domain/memory_inventory.py`) compiles current life-memory from gated vault rows. It does not persist, decide retention, or replace SEC-06. Forgotten rows are absent because forget is SQL DELETE. Superseded rows remain in the vault for lineage but are absent from **current** inventory.

**Recorded finding (slice 4 freeze, not a second store):** the projector also hides elapsed-TTL rows before `expire_ttl()` runs, so inventory can look forgotten while descendants still sit in `derived_records`. C30 must not treat inventory absence as proof that GC ran. The projector is not a retention policy; inventory owns no extra state.

**The vault remembers. The inventory explains.**

Correction mints a new retained assertion with `supersedes` + `derived_from` pointing at the prior id. In-place payload rewrite of an existing retained id is forbidden.

`MODEL_INFERRED` display-maps to `POSSIBLE` and must never collapse to `KNOWN`. The retention gate still refuses to persist inferred assertions as durable; the mapping is defense-in-depth if such a row is ever present.

Inspectable `why` answers with purpose, provenance **refs**, `derived_from`, and `retained_at`. Provenance may point at a source id; inventory payloads must not include raw email/chat bodies.

Forget is exposed as a capability (`action=forget_retained_assertion`) that invokes the existing cascade. C30 Brain UI compiles from this inventory; it must not invent a second truth database.

## Implementation dependency order

```text
RetentionPolicy / RetentionDecision  ← slice 1
  ↓
small durable assertion store         ← slice 2
  ↓
deletion + derivative invalidation    ← slice 3
  ↓
MemoryInventory projection            ← slice 4
  ↓
only then richer Life Graph UI (C30)
```

## Consequences

- `packages/domain/retention_gate.py` is the canonical retention decision function.
- Evidence packs and respond grounding remain ephemeral; they do not write durable memory.
- Freeze tests (Ceramics, Detective, Forget, Third-party, Purpose-expiry) gate future Life Graph work.
- C29 slices 1–4 are frozen: establish → retain → persist → expire/forget/correct → inspect. Brain UI, semantic recall, and crypto are not C29.
- C30 Brain UI must compile from `MemoryInventory` + `DurableAssertionStore` + SEC-06 vault rows, not invent parallel truth. Inventory absence is not proof that GC ran.
- Slice 4 freeze tests (Why, Correction, Forget, Detective, No-raw-source, Epistemic display) gate that UI.

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
