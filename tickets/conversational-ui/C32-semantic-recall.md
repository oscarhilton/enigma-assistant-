# C32 — Semantic recall slice A (index + governed-memory filter)

**Status:** done · **frozen** (slice A · [#96](https://github.com/oscarhilton/enigma-assistant-/pull/96))  
**Branch:** `ticket/C32-semantic-recall`  
**Domain:** conversational-ui  
**May edit:** `packages/domain/src/personal_enigma/domain/semantic_recall.py`, `packages/domain/src/personal_enigma/domain/__init__.py`, `packages/domain/tests/test_semantic_recall.py`, `packages/embeddings/**`, `apps/api/src/personal_enigma/api/storage/semantic_recall.py`, `apps/api/tests/test_c32_vault_semantic_recall.py`, `docs/adr/037-*.md`, `docs/architecture/data-retention.md`, `docs/architecture/enigma-master-gap-analysis.md`, `tickets/conversational-ui/**`, `tickets/README.md`

**Must not edit:** C29 life-memory vault/inventory modules · C30 Brain UI · C31 Goose · crypto / compartment keys · `respond_grounding.py` · raw-source embedding of emails/chats as recall memory

**Hard depends:** [C29](./C29-life-memory-and-retention.md) frozen MemoryInventory  
**Soft (~):** [M14](../retrieval/M14-local-embeddings.md) local embeddings package

**ADR:** [ADR-037](../../docs/adr/037-semantic-recall-index-not-memory.md)

## Goal

Prove that semantic recall is an **index over governed truth**, not a second memory:

> Recall may find governed memory. It may not create, promote, resurrect, or retain it.

> Retrieval may be approximate. Authority may not be.

> The index may be stale. The authority layer may not be.

## Slice A only

```text
structured retained assertion
  → reduced semantic representation
  → local candidate lookup
  → assertion IDs
  → governed-memory filter
  → actual current assertions
```

**Required order (must not flip):**

```text
approximate retrieval
  → candidate assertion IDs
  → governed-memory lookup
  → current / retained / valid check
  → only then expose assertion
```

If that order ever becomes “embedding hit = usable memory,” this slice has failed.

**Freeze question:** Can recall be wrong about what looks relevant without ever being wrong about what Enigma is allowed to treat as current memory? If yes, slice A is doing what it should.

## Review invariants (do not add more)

1. Recall is an index, never a truth store.
2. Candidates resolve back to governed assertion IDs.
3. Current retention / expiry / forget state is checked **after** retrieval.
4. Similarity never upgrades epistemic status.
5. Forgotten memory cannot be resurrected by a stale index.
6. Recall does not itself create or retain anything.

## Deliverables

- [x] Reduce retained assertions to structured meaning before vectorising (never raw email/chat bodies)
- [x] Local candidate index keyed by assertion ID (`packages/embeddings`)
- [x] Governed-memory filter over current MemoryInventory / current retained state
- [x] Pipeline order explicit in code and tests
- [x] Ceramics freeze + inverse re-establishment freeze
- [x] [ADR-037](../../docs/adr/037-semantic-recall-index-not-memory.md)

## Freeze tests

| Test | Assertion |
| --- | --- |
| **Ceramics** | retain → index → recall finds it; forget → stale embedding may exist; query "ceramics" → candidate may be found internally → filter rejects → Enigma does not receive ceramics as current memory |
| **Inverse** | forget ceramics → later independent evidence re-establishes → new governed assertion + new lineage → recall may find the **new** assertion. Deletion is not a permanent semantic blacklist. |
| **Order** | Approximate retrieval cannot skip the governed-memory filter |
| **Epistemic** | Similarity does not upgrade `MODEL_INFERRED` (or any status) |
| **No-create** | Recall has no retain/store path |
| **No-raw-source** | Reduction uses subject/predicate/value, not evidence bodies |

## Explicit non-goals

- Slice B crypto (compartment keys, key destruction, stronger unrecoverability)
- C30 Brain / Cortex / Case File UI
- C31 Goose choreography
- Ontology / psychographic memory
- Hosted embeddings for raw private text
- Giving recall retention, promotion, or resurrection powers

## Definition of done

Recall can be wrong about relevance and still cannot be wrong about what is current governed memory.

## Freeze (2026-08-18)

**Frozen at** `9eb7477`. Slice A freeze review: **PASS.**

**Freeze question:** Can recall be wrong about relevance without ever being wrong about what Enigma may treat as current memory? **Yes.**

Pipeline (only legal order): approximate retrieval → candidate assertion IDs → governed-memory lookup → current / retained / valid check → only then expose. An embedding hit is never usable memory.

Ceramics: retain → index finds it; forget → stale index entry may still exist; query ceramics → candidate may be returned internally → governed-memory filter rejects it → Enigma never receives it as current memory.

Inverse: forget is not a semantic blacklist; later genuine re-establishment is new lineage and may be recalled.

Remaining crypto slice B, C30 Brain UI, and C31 Goose are **not** this slice.

## Test plan

```bash
uv run pytest packages/domain/tests/test_semantic_recall.py packages/embeddings/tests/test_c32_semantic_recall.py apps/api/tests/test_c32_vault_semantic_recall.py -q
uv run ruff check packages/domain/src/personal_enigma/domain/semantic_recall.py packages/embeddings/src/personal_enigma/embeddings/governed_index.py apps/api/src/personal_enigma/api/storage/semantic_recall.py
uv run basedpyright packages/domain/src/personal_enigma/domain/semantic_recall.py packages/embeddings/src/personal_enigma/embeddings/governed_index.py apps/api/src/personal_enigma/api/storage/semantic_recall.py
```
