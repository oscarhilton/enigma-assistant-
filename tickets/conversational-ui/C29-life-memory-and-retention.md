# C29 — Life memory, retention gate, and third-party ethics

**Status:** done · **frozen** (slices 1–4 lifecycle)  
**Branch:** `ticket/C29-life-memory-retention`  
**Domain:** conversational-ui  
**May edit:** `packages/domain/src/personal_enigma/domain/retention.py`, `packages/domain/src/personal_enigma/domain/retention_gate.py`, `packages/domain/src/personal_enigma/domain/durable_assertions.py`, `packages/domain/src/personal_enigma/domain/memory_inventory.py`, `packages/domain/src/personal_enigma/domain/__init__.py`, `packages/domain/tests/test_retention_gate.py`, `packages/domain/tests/test_memory_inventory.py`, `apps/api/src/personal_enigma/api/storage/retention_vault.py`, `apps/api/src/personal_enigma/api/storage/retention_forget.py`, `apps/api/src/personal_enigma/api/storage/memory_inventory.py`, `apps/api/tests/test_c29_*.py`, `docs/architecture/data-retention.md`, `docs/adr/036-*.md`, `docs/architecture/enigma-master-gap-analysis.md`, `tickets/conversational-ui/**`

**Must not edit:** C26 grounding · `respond_grounding.py` · C27 continuity · C28 event spine · SEC-06 forget cascade invariants · new psych-profile storage · Goose memory UI · Life Graph projections

**Hard depends:** [C26](./C26-grounded-assertions-epistemics.md) (frozen)  
**Soft (~):** [SEC-06](../security/SEC-06-retention-memory-decay-forget.md) lineage/forget · [C30](./C30-brain-cortex-case-file.md) Brain projection follow-on

**ADR:** [ADR-036](../../docs/adr/036-retention-gate-life-memory.md)

## Goal

Answer one question: **Given Enigma can establish truth and act safely, what information is justified in surviving beyond the work that produced it?**

Critical separation: **ESTABLISHED AS TRUE ≠ JUSTIFIED TO RETAIN**

## Two rules (non-negotiable)

1. **Truth does not imply retention.**
2. **Confirmation grants epistemic status. Purpose grants retention.**

## Pipeline

```text
GroundedAssertion
  → is it established strongly enough?
  → is there a legitimate user-owned purpose?
  → is retention proportionate?
  → for how long?
  → DURABLE / TTL / EPHEMERAL / REJECT
```

## Scope (7 items only — resist expansion)

| # | Item | Slice 1 | Follow-on |
| --- | --- | --- | --- |
| 1 | retention decision | `evaluate_retention()` | — |
| 2 | retention class / lifetime | `RetentionDecision` + `RetentionOutcome` | GC wiring |
| 3 | retention purpose | `RetentionPurpose.LIFE_FACT` etc. | purpose UI |
| 4 | provenance preservation | `provenance_refs` on decision | vault mapping (slice 2) |
| 5 | third-party restrictions | gate rejects profiling predicates | audit |
| 6 | correction / deletion | `forget_retained_assertion()` + SEC-06 lineage graph | inventory API (slice 4) |
| 7 | derivative invalidation | full SEC-06 graph via `retention_forget.py` | — |

## First memory model (boring & practical only)

**In:** people, relationships, projects, commitments, dates, birthdays, plans, concrete preferences, gift history, places, dependencies, shared conventions.

**Out:** personality vectors, relationship strength, inferred psychology, giant ontology.

## Implementation dependency order (mandatory)

```text
RetentionPolicy / RetentionDecision          ← slice 1 · frozen
  ↓
small durable assertion store                 ← slice 2 · frozen
  ↓
deletion + derivative invalidation            ← slice 3 · frozen
  ↓
MemoryInventory projection                    ← slice 4 · frozen
  ↓
only then richer Life Graph UI (C30)
```

C29 lifecycle is complete: **establish → retain → persist → expire/forget/correct → inspect**. Brain UI, semantic recall, and crypto are **not** C29.

## Builds on SEC-06 (do not duplicate)

| Layer | Owner | C29 uses it for |
| --- | --- | --- |
| `DerivedRecord`, `LineageMetadata`, decay, forget graph | SEC-06 · `apps/api/storage/` | mapping durable assertions → vault rows (slice 2+) |
| `SensitiveInferenceClass` write guard | SEC-06 · `storage/sensitive.py` | complementary to gate third-party rules |
| Forget API stubs | SEC-06 · `routes/forget.py` | user-facing delete after gate approves scope |
| `GroundedAssertion.retention_class` hint | C26 | input hint only — gate decides |

C29 adds the **semantic gate**; SEC-06 retains **storage-plane** enforcement.

## Goose boundary

THE Goose is **presentation-only**. It may retrieve retained facts for display later; it **never** decides what gets remembered. Enigma establishes; retention policy decides survival ([ADR-036](../../docs/adr/036-retention-gate-life-memory.md)).

## Deliverables

### Slice 1 (this branch)

- [x] `RetentionDecision`, `RetentionOutcome`, `RetentionRejectionReason` in `packages/domain/retention_gate.py`
- [x] `evaluate_retention(GroundedAssertion) → RetentionDecision`
- [x] Life-memory `RetentionPurpose` values on existing enum
- [x] Stub `DurableAssertionStore` + `InMemoryDurableAssertionStore`
- [x] Freeze tests (5 scenarios) in `packages/domain/tests/test_retention_gate.py` and `apps/api/tests/test_c29_retention_freeze.py`
- [x] [ADR-036](../../docs/adr/036-retention-gate-life-memory.md)

### Slice 2 (vault bridge)

- [x] `retention_vault.py` — `map_retention_to_derived_record()`, `VaultDurableAssertionStore`
- [x] Gate → vault write for DURABLE/TTL only (`assert_retention_write_allowed`)
- [x] Epistemic non-upgrade at write boundary (payload matches assertion status)
- [x] Lineage refs: `assertion:{id}`, `retention_decision:{id}`, evidence + provenance refs
- [x] Minimal `forget_retained_assertion()` cascade for child retained rows
- [x] Bridge + freeze tests in `apps/api/tests/test_c29_retention_vault_bridge.py`

### Slice 3 (forget propagation + TTL expiry)

- [x] `retention_forget.py` — `resolve_retained_assertion_forget_plan()`, `forget_retained_assertion_with_propagation()`
- [x] Transitive lineage cascade via SEC-06 `derived_source_deps` (not payload-only children)
- [x] Independent evidence survives (`EV_*` only if a live source/assertion/derived row; dangling tokens do not save exclusive descendants)
- [x] TTL expiry (`expire_retained_assertions()`) — same cascade function as explicit forget (`trigger=ttl_expiry`)
- [x] Current memory is the vault derived table after semantic delete (`list_current_memory_records`, `current_memory_record_ids_mentioning`) — not a hide-filter on retained rows
- [x] Survivors lose forgotten lineage refs (propagate invalidation)
- [x] Forget audit metadata — ids only, never deleted private content
- [x] Freeze tests in `apps/api/tests/test_c29_forget_propagation.py` (Ceramics cascade + grandchild, TTL expiry, Re-establishment, independent-evidence execution)

### Slice 3 invariants (enforced in code + tests)

1. **Forgetting is semantic** — unjustified derived rows are deleted from `derived_records`, not hidden from one projection
2. **Lineage determines invalidation** — B justified only by A → forget(A) deletes B (self-refs and dangling `EV_*` are not independent evidence)
3. **Independent evidence survives** — live source records / other retained assertions keep the row; forgotten parent refs are stripped from lineage
4. **TTL expiry = governed forgetting** — `expire_retained_assertions()` calls `forget_retained_assertion_with_propagation(..., trigger="ttl_expiry")`
5. **Expired / forgotten memory cannot appear as current** — deleted rows absent from `list_current_memory_records` (all derived rows, not just retained assertions)
6. **Deletion must not rewrite history** — audit records ids; no deleted payload content
7. **Forget does not mutate epistemic class** — unavailable ≠ false; re-establishment creates a new row with its own status and lineage
8. **Deletion is not an epistemic blacklist** — the same proposition may be retained again from later independent evidence

### Freeze-readiness notes (slice 3)

Semantic freeze line: `retain → derive → forget / expire → propagate invalidation → current memory no longer exposes unjustified descendants`.

Physical vs logical: C29 forget is **SQL DELETE of derived rows** (plus lineage rewrite on survivors). SQLCipher page encryption remains; there is **no per-row key destruction or VACUUM shred**. Freeze readiness at this layer is: forgotten content cannot participate in current memory or reconstruct unjustified descendants. Cryptographic destruction of residual ciphertext is a later storage-hardening layer — this slice does not pretend to provide it.

Inventory API is slice 4 (this freeze). Brain UI / Goose memory UI remain C30 / C31. Slice 4 is the **read model** (projection), not the Brain UI.

### Slice 4 (Memory inventory / Brain read model)

- [x] `MemoryInventory` projection over current retained assertions (`packages/domain/memory_inventory.py`)
- [x] Display statuses: `KNOWN` / `POSSIBLE` / `STALE` / `CONFLICTED` / `EXPIRING`
- [x] `MODEL_INFERRED` maps to `POSSIBLE` and never collapses to `KNOWN`
- [x] Vault query `list_memory_inventory()` — forgotten/expired/superseded rows absent from current inventory
- [x] Inspectable `why` (purpose, provenance refs, derived_from, retained_at) without raw source bodies
- [x] Forget capability flag hooks existing `forget_retained_assertion()` — no parallel delete
- [x] `correct_retained_assertion()` mints a new row with `supersedes` / lineage (no in-place rewrite)
- [x] Freeze tests: Why, Correction, Forget, Detective, No-raw-source, Epistemic display (`packages/domain/tests/test_memory_inventory.py`, `apps/api/tests/test_c29_memory_inventory.py`)

### Out of C29 (do not reopen this ticket)

- [ ] C30 Brain / Cortex / Case File UI compiles from this inventory — does not invent a second store
- [ ] Semantic recall / embeddings — *Recall may find governed memory. It may not create, promote, resurrect, or retain it.*
- [ ] Crypto key destruction of residual vault ciphertext

**The vault remembers. The inventory explains.**

## Freeze tests (acceptance criteria — must stay green)

| Test | Assertion |
| --- | --- |
| **Ceramics** | Confirmed preference may become retainable; inferred preference does **not** silently become durable |
| **Detective** | Rich source material yields useful life facts, not a dossier (inventory must not surface inferred psychology as `KNOWN`) |
| **Forget** | Delete retained fact → invalidate unjustified summaries/vectors/derived assertions; forgotten/expired items absent from current inventory |
| **Third-party** | Remember "Maya likes ceramics"; reject "Maya is emotionally dependent on…" unless extraordinary explicit product justification |
| **Purpose-expiry** | Fact retained for temporary case does not live forever merely because once useful |
| **Why** | “Why do you remember Maya likes ceramics?” has purpose, provenance refs, derived_from, retained_at |
| **Correction** | Correcting retained information mints a new superseding row; prior payload is unchanged |
| **No-raw-source** | Inspecting inventory does not dump raw email/chat bodies; provenance may point at source ids |
| **Epistemic display** | `MODEL_INFERRED` remains `POSSIBLE` and never displays as `KNOWN` |

## Explicit non-goals

- Reopening C26 grounding, respond_grounding, C27 continuity, C28 event spine
- Life Graph / Brain **UI** (→ C30) — C29 slice 4 owns the inspectable inventory read model only
- Goose memory UI (→ C31)
- Personality inference, relationship strength, psychographic storage
- LLM writes durable memory directly
- Raw-source retention policy changes
- Second forget graph parallel to SEC-06

## Freeze (2026-08-18)

Slice 4 freeze review: **Q1 PASS WITH NOTES · Q2 PASS · Q3 PASS WITH NOTES · Q4 PASS. Overall: Freeze C29.**

Lifecycle complete: establish → retain → persist → expire/forget/correct → inspect.

**Recorded finding (not a blocker, not a second store):** the inventory projector also hides elapsed-TTL rows before `expire_ttl()` runs, so inventory can look forgotten while descendants still sit in `derived_records`. Forget is SQL DELETE. C30 must not treat inventory absence as proof that GC ran. Do not add inventory-owned state. Do not make the projector a retention policy.

Remaining Brain UI / semantic recall / crypto / Goose choreography are **not** C29.

## Definition of done (programme)

Enigma can retain useful concrete facts for the user while refusing to turn other people into psychological dossiers — with an inspectable gate between establishment and persistence, and an inspectable inventory that explains current memory without becoming a second store.

## Test plan

```bash
uv run pytest packages/domain/tests/test_retention_gate.py packages/domain/tests/test_memory_inventory.py apps/api/tests/test_c29_retention_freeze.py apps/api/tests/test_c29_retention_vault_bridge.py apps/api/tests/test_c29_forget_propagation.py apps/api/tests/test_c29_memory_inventory.py -q
uv run ruff check packages/domain/src/personal_enigma/domain/retention_gate.py packages/domain/src/personal_enigma/domain/durable_assertions.py packages/domain/src/personal_enigma/domain/memory_inventory.py apps/api/src/personal_enigma/api/storage/retention_vault.py apps/api/src/personal_enigma/api/storage/retention_forget.py apps/api/src/personal_enigma/api/storage/memory_inventory.py
uv run basedpyright packages/domain/src/personal_enigma/domain/retention_gate.py packages/domain/src/personal_enigma/domain/memory_inventory.py apps/api/src/personal_enigma/api/storage/retention_forget.py apps/api/src/personal_enigma/api/storage/memory_inventory.py
```

Regression: SEC-06 forget/lineage tests must remain green (`apps/api/tests/test_sec06_forget_lineage.py`).
