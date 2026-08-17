# SEC-06 — Retention policy, memory decay, and forget operations

**Status:** done  
**Branch:** `ticket/SEC06-retention-memory-decay-forget`  
**Domain:** security  
**May edit:** `apps/api/src/personal_enigma/api/storage/**`, `apps/worker/**` (GC jobs), `packages/domain/**` (retention metadata fields only), `apps/api/tests/**`, `docs/architecture/data-retention.md`, `docs/adr/022-private-vault-storage.md`  
**Must not edit:** `packages/ingestion/.../sources/gmail.py` (SEC-04), egress gate (SEC-02), demo simulation roots

**Hard depends:** [SEC-01](./SEC-01-secrets-encrypted-storage.md)  
**Soft (~):** [SEC-00](./SEC-00-personal-data-threat-model.md), [C05e](../conversational-ui/C05e-recent-source-queries.md) (recent-source tools must respect TTL)

**Spec source:** [data-retention.md](../../docs/architecture/data-retention.md) · [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md)

## Goal

Enforce the **retention & reconstructability boundary** from [data-retention.md](../../docs/architecture/data-retention.md) and the **pseudonymous shadow shape** from [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md).

**SEC-06 is the co-equal other half of [SEC-01](./SEC-01-secrets-encrypted-storage.md).** SEC-01 protects what is retained (encryption); SEC-06 controls whether data should exist at all (retention, decay, forget). Neither alone is sufficient.

> **The safest Enigma isn't the one that can remember everything. It's the one that knows what is worth forgetting.**

> **No retained derivative may outlive its justification merely because it is derived.**

Pilot bias: **deliberately too aggressive on forgetting** — extend TTLs when product need is proven, not shrink later.

## Architectural reference

- [data-retention.md](../../docs/architecture/data-retention.md)
- [ADR-023 — Pseudonymous shadow](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md)
- [ADR-022 — Retention & reconstructability boundary](../../docs/adr/022-private-vault-storage.md#retention--reconstructability-boundary)

## Deliverables

### Four-layer lifecycle pipeline

- [x] Layer model: **SOURCE WORLD** → **ACTIVE PRIVATE STATE** → **PSEUDONYMOUS SHADOW** → **FORGET**
- [x] SOURCE WORLD: PRIVATE_RAW blobs — raw, identifiable, short-lived (7 day pilot default)
- [x] ACTIVE PRIVATE STATE: purpose-bound structured facts — only what Enigma currently needs
- [x] PSEUDONYMOUS SHADOW: enums, buckets, state transitions — low narrative reconstructability
- [x] FORGET: recoverability → zero within Enigma — terminal state, not TTL alone

### DECAY vs FORGET (hard distinction)

- [x] **DECAY** pipeline: detail↓ precision↓ linkability↓ while utility retained (active → shadow compression)
- [x] **FORGET** pipeline: recoverability → zero — graph operation, not rename-to-`PERSON_Q7`
- [x] Anti-pattern test: "forget person" must not leave full correspondence graph under new alias
- [x] Document DECAY and FORGET as separate code paths with separate tests

### Lineage metadata (formal, lightweight)

Shadow and active-state records carry lineage for deterministic forget:

| Field | Example |
| --- | --- |
| `derived_from` | `[SRC_123, SRC_188]` |
| `purpose` | `OPEN_LOOP_TRACKING` |
| `retention_class` | `ACTIVE_UNTIL_RESOLVED` |
| `expires_after_resolution` | `30d` |

- [x] Lineage fields on all durable PRIVATE_DERIVED rows
- [x] `forget(source_id)` graph resolver:
  - What depends **exclusively** on this source?
  - What has **independent evidence**?
  - What **must disappear**?
  - What can **remain but lose confidence**?
- [x] "Forget everything about X" = graph operation — not best-effort DB delete

### Derivative cascade (exhaustive)

On source delete, blob expiry, or scoped forget, cascade **all** derivative classes:

- [x] Embeddings, FTS rows, vector index entries
- [x] Summaries and semantic labels
- [x] Interaction-frequency aggregates
- [x] Inferred relations (lineage-bound)
- [x] Cached retrieval chunks
- [x] Source-derived features
- [ ] Historical audit material tied to forgotten scope
- [x] Graph edges with no independent evidence after cascade
- [x] Test: zero orphaned derived rows after any forget path

### Pseudonymous shadow schema rules

- [x] Derived attributes over exact values: time buckets, coarse region, money bands, importance/response enums — not raw prose or exact geo/financial
- [x] Source evidence via encrypted `source_id` / `blob_ref` only — never inline body text in durable rows
- [x] Decay compresses active private state → shadow **before** TTL expiry where possible (progressive abstraction)

### Purpose-scoped aliases

- [ ] Vault graphs use scope-local `PERSON_*` namespaces (project / social / egress) — not one global linkage graph
- [ ] Identity resolver ([packages/identity](../../packages/identity)) holds equivalence mapping separately from durable graph edges
- [ ] Document migration from stable global alias to scoped alias in schema / resolver

### Per-class retention enforcement

- [x] GC jobs for blob expiry, resolved-obligation expiry (30–90 days), calendar horizon trim
- [ ] People graph retains identity + alias + minimal relationship state — **not** full correspondence history
- [x] Configurable TTL per class in `config.json` (non-secret)

### Embedding / index expiry tied to source

- [x] On SourceRecord delete or blob expiry: cascade remove all derivative classes listed above
- [x] Re-fetch from provider → re-embed allowed; embeddings are **reproducible, not precious**
- [x] Test: no orphaned index rows after source GC

### Sensitive inference guardrails

- [x] No **permanent** storage of: medical, sexuality, political, substance, intimate relationships, financial distress, behavioural routines (pilot invariant)
- [x] Ephemeral inference for answering allowed; persistent sensitive labels require explicit future approval path (document stub / reject at write)
- [x] Derived-state deletion includes inferred labels and graph edges

### Forget operations (API + product hooks)

- [x] **Inventory:** "What do you remember about me?" — scoped summary of retained classes (not raw dump)
- [x] **Provenance:** "Why are you remembering that?" — source id, retention reason, expiry, lineage
- [x] **Scoped forget:** "Forget everything about that project/person/before date" — graph operation with full derivative cascade
- [x] Forget is cryptographic/structural deletion — not UI hide

### Red-line reconstructability documentation

- [ ] Operator doc: red-line test procedure before extending any TTL or amber-zone class
- [ ] Three zones (Green / Amber / Red) referenced in runbook

## Acceptance criteria

- [x] Per-class TTL table from [data-retention.md](../../docs/architecture/data-retention.md) implemented in `config.json` + GC jobs
- [x] Regression: C05e Demo chat index expires raw quote bodies (7-day `RAW_TTL`) while `apply_chat_messages` still folds independently justified derived facts (`EXPIRY ≠ LOSS OF ALL UTILITY`)
- [x] DECAY and FORGET tested as separate paths with distinct outcomes
- [x] Lineage fields present on durable derived rows; `forget(source_id)` graph resolver tested
- [x] Derived state cascades on source delete, blob expiry, and scoped forget — zero orphaned rows across **all** derivative classes
- [x] Sensitive inferences **not persisted permanently** for pilot (write-path guard or reject; ephemeral answer-only allowed)
- [x] Forget API stubs (inventory, provenance, scoped delete) **or** follow-on UI ticket linked from this ticket
- [ ] SEC-05 Q11–Q16 evidence links from this ticket (Q16 runner in [SEC-07](./SEC-07-shadow-reconstruction-benchmark.md))

## Test plan

- Integration: ingest → wait/simulate TTL → GC → verify blob gone + full derivative cascade
- Integration: decay path → verify active state compressed to shadow enums (utility retained)
- Integration: forget-by-person → verify graph operation removes all exclusive dependencies; no alias-rename anti-pattern
- Unit: `forget(SRC_123)` resolver — exclusive vs independent evidence cases
- Unit: sensitive inference classifier rejects permanent write (pilot classes)
- Regression: red-line zone table matches [data-retention.md](../../docs/architecture/data-retention.md)

## Privacy constraints

- Inventory APIs must not return raw email bodies or attachment bytes
- Forget operations must not log deleted content — ids and scope only

**Unlocks:** SEC-05 retention gate questions (Q11–Q16) · [SEC-07](./SEC-07-shadow-reconstruction-benchmark.md)

## Related ADR

[ADR-021](../../docs/adr/021-personal-data-security-boundary.md) · [ADR-022](../../docs/adr/022-private-vault-storage.md) · [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md) · [SEC-01](./SEC-01-secrets-encrypted-storage.md) (co-equal half) · [data-retention.md](../../docs/architecture/data-retention.md)
