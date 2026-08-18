# C29 — Life memory, retention gate, and third-party ethics

**Status:** in_progress (slice 2 — vault bridge)  
**Branch:** `ticket/C29-life-memory-retention`  
**Domain:** conversational-ui  
**May edit:** `packages/domain/src/personal_enigma/domain/retention.py`, `packages/domain/src/personal_enigma/domain/retention_gate.py`, `packages/domain/src/personal_enigma/domain/durable_assertions.py`, `packages/domain/src/personal_enigma/domain/__init__.py`, `packages/domain/tests/test_retention_gate.py`, `apps/api/tests/test_c29_*.py`, `docs/architecture/data-retention.md`, `docs/adr/036-*.md`, `docs/architecture/enigma-master-gap-analysis.md`, `tickets/conversational-ui/**`

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
| 6 | correction / deletion | stub `InMemoryDurableAssertionStore.forget()` | SEC-06 bridge (slice 2 minimal) |
| 7 | derivative invalidation | stub cascade | full SEC-06 graph (slice 3) |

## First memory model (boring & practical only)

**In:** people, relationships, projects, commitments, dates, birthdays, plans, concrete preferences, gift history, places, dependencies, shared conventions.

**Out:** personality vectors, relationship strength, inferred psychology, giant ontology.

## Implementation dependency order (mandatory)

```text
RetentionPolicy / RetentionDecision          ← slice 1 (this branch)
  ↓
small durable assertion store
  ↓
deletion + derivative invalidation (wire SEC-06 forget)
  ↓
only then richer Life Graph projections (C30)
```

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

### Slice 3+

- [ ] Wire forget/correction to SEC-06 `forget_source` graph (full propagation)
- [ ] Purpose-expiry GC for TTL decisions
- [ ] Inventory API surfaces life-memory assertions alongside derived records

## Freeze tests (acceptance criteria — must stay green)

| Test | Assertion |
| --- | --- |
| **Ceramics** | Confirmed preference may become retainable; inferred preference does **not** silently become durable |
| **Detective** | Rich source material yields useful life facts, not a dossier |
| **Forget** | Delete retained fact → invalidate unjustified summaries/vectors/derived assertions |
| **Third-party** | Remember "Maya likes ceramics"; reject "Maya is emotionally dependent on…" unless extraordinary explicit product justification |
| **Purpose-expiry** | Fact retained for temporary case does not live forever merely because once useful |

## Explicit non-goals

- Reopening C26 grounding, respond_grounding, C27 continuity, C28 event spine
- Life Graph / Brain projection (→ C30)
- Goose memory UI (→ C31)
- Personality inference, relationship strength, psychographic storage
- LLM writes durable memory directly
- Raw-source retention policy changes
- Second forget graph parallel to SEC-06

## Definition of done (programme)

Enigma can retain useful concrete facts for the user while refusing to turn other people into psychological dossiers — with an inspectable gate between establishment and persistence.

## Test plan

```bash
uv run pytest packages/domain/tests/test_retention_gate.py apps/api/tests/test_c29_retention_freeze.py apps/api/tests/test_c29_retention_vault_bridge.py -q
uv run ruff check packages/domain/src/personal_enigma/domain/retention_gate.py packages/domain/src/personal_enigma/domain/durable_assertions.py apps/api/src/personal_enigma/api/storage/retention_vault.py
uv run basedpyright packages/domain/src/personal_enigma/domain/retention_gate.py
```

Regression: SEC-06 forget/lineage tests must remain green (`apps/api/tests/test_sec06_forget_lineage.py`).
