# ADR-037: Semantic recall is an index, never a truth store

**Status:** Accepted · **frozen** (slice A, 2026-08-18, `9eb7477`)  
**Date:** 2026-08-18

> **Recall may find governed memory. It may not create, promote, resurrect, or retain it.**
>
> **Retrieval may be approximate. Authority may not be.**
>
> **The index may be stale. The authority layer may not be.**

## Context

[C29](../../tickets/conversational-ui/C29-life-memory-and-retention.md) froze the life-memory lifecycle: establish → retain → persist → expire/forget/correct → inspect. [MemoryInventory](./036-retention-gate-life-memory.md) is a projection over governed vault state.

[M14](../../tickets/retrieval/M14-local-embeddings.md) already provides local embeddings. Those vectors must not become a second biography, a resurrection path for forgotten facts, or a way to upgrade epistemic status by similarity.

## Decision

### 1. Slice A pipeline (only legal order)

```text
structured retained assertion
  → reduced semantic representation
  → local candidate lookup
  → assertion IDs
  → governed-memory lookup
  → current / retained / valid check
  → only then expose assertion
```

Approximate retrieval may return stale or irrelevant IDs. An embedding hit is never usable memory. Current retention / expiry / forget state is checked **after** retrieval.

### 2. Reduce meaning before vectorising

Index `subject` / `predicate` / `value` claims (e.g. "Maya likes ceramics"), not raw emails or chat bodies. Vectors address governed assertion IDs.

### 3. Authority stays with governed memory

Candidates resolve through current [MemoryInventory](./036-retention-gate-life-memory.md) / current retained vault state. Forgotten, expired (no longer current), and superseded items are not exposed even if a stale embedding still exists.

Forgetting is a lifecycle event, not a curse on a concept: later independent evidence may mint a **new** assertion with new lineage, and recall may find that new id.

### 4. Similarity is not establishment

`RecalledAssertion` exposes the governed assertion unchanged. Similarity scores are metadata. They must not call the retention gate, must not change `EpistemicStatus`, and must not set `DerivationKind.SEMANTIC_SIMILARITY` as a promotion.

### 5. Recall has no write path

The recall function accepts an index and an authority. It does not `store`, `evaluate_retention`, or resurrect forgotten rows.

### 6. Local embeddings only

Reuse `packages/embeddings` with the existing fake/local-only embedders. No hosted embedding of private text. Remote inference remains disable-able.

## Slice B (explicitly not now)

Compartment keys, key destruction, and stronger cryptographic unrecoverability are a later storage-hardening slice. C32 does not implement them.

C30 Brain UI and C31 Goose are not recall, and recall is not a UI.

## Consequences

- `packages/domain/semantic_recall.py` owns pipeline order, reduction, and the governed-memory filter.
- Approximate candidate ID lookup lives in `packages/embeddings` (currently `packages/embeddings/src/personal_enigma/embeddings/index.py`). Embeddings remain a separate slice; recall tests may use any `CandidateAssertionIndex`.
- `apps/api/storage/semantic_recall.py` (`VaultInventoryAuthority`, RECON-05C) adapts current MemoryInventory + vault payloads as the authority. Index hits and leftover vault rows cannot skip that adapter.
- Freeze tests: ceramics stale-index rejection, inverse re-establishment, epistemic non-upgrade, no-create, no-raw-source.

## Non-goals

- Not a second memory store.
- Not crypto slice B.
- Not Brain UI or Goose.
- Not an ontology.
- Not permission for the LLM to write durable memory via similarity.

## Related

- [ADR-036](./036-retention-gate-life-memory.md)
- [data-retention.md](../architecture/data-retention.md)
- [C32](../../tickets/conversational-ui/C32-semantic-recall.md) (donor slice A)
- [RECON-05C](../../tickets/conversational-ui/RECON-05C-semantic-recall-authority.md)
- [M14](../../tickets/retrieval/M14-local-embeddings.md)
