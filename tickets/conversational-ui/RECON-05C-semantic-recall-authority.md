# RECON-05C — Vault-backed semantic recall authority

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `cursor/recon-05c-semantic-recall-authority-e4af` |
| Domain | `conversational-ui` |
| Programme | Dependency-minimal recovery of C32 slice A **authority** only |

Donor: `origin/ticket/C32-semantic-recall` @ `ebaf592c5ebd601fa920ac2e15531e56aae8e315`. Current `main` is truth. RECON-04 / RECON-05A / RECON-05B are canonical and must not be re-ported.

## Goal

Wire current domain `semantic_recall` to current vault-backed `MemoryInventory` so approximate index hits cannot become memory.

> **index ≠ authority** ([ADR-037](../../docs/adr/037-semantic-recall-index-not-memory.md))

Embedding/index hits may propose candidate assertion IDs. Only inventory/vault authority may establish recall eligibility / currentness.

## Package boundary (hard)

May edit:

- `apps/api/src/personal_enigma/api/storage/semantic_recall.py`
- `apps/api/tests/test_recon05c_semantic_recall_authority.py`
- `tickets/conversational-ui/RECON-05C-semantic-recall-authority.md`
- `docs/adr/037-semantic-recall-index-not-memory.md` (wiring note only)
- `docs/architecture/data-retention.md` (wiring note only)

Must not edit:

- `apps/api/src/personal_enigma/api/storage/vault.py` (RECON-04)
- `apps/api/src/personal_enigma/api/storage/retention_vault.py` (RECON-05A/05B)
- `apps/api/src/personal_enigma/api/storage/retention_forget.py` (RECON-05B)
- `apps/api/src/personal_enigma/api/storage/memory_inventory.py` (RECON-05B)
- `packages/domain/**` (current `semantic_recall` / inventory stay)
- `packages/embeddings/**`
- worker scheduling, HTTP routes, UI, C28, life scripts, kernel/router

## Hard depends

- RECON-04 SEC-06 vault foundation
- RECON-05A retention → vault adapter
- RECON-05B forget / TTL / inventory

## Soft depends (~)

- [M14](../retrieval/M14-local-embeddings.md) local embeddings — **not required for this tranche**. Domain `CandidateAssertionIndex` is enough. Embeddings stay a later independent slice.

## Acceptance criteria

- [x] `VaultInventoryAuthority` answers `GovernedMemoryAuthority.current_retained`
- [x] Inventory absence (forgotten / elapsed TTL / superseded) rejects even if a stale index or leftover vault row exists
- [x] Exposed assertions preserve provenance refs and epistemic status (no similarity upgrade)
- [x] Recall has no write path (`store` / `forget` / `evaluate_retention` / `expire_ttl`)
- [x] Embeddings package is not imported by the adapter or its tests

## Explicit non-goals

- Embeddings / `LocalCandidateIndex` / governed vector index
- Worker scheduling
- HTTP routes / Brain UI / Goose
- C28 event spine, life scripts, kernel/router
- Crypto slice B
- Re-porting C29 vault/forget/inventory

## Test plan

```bash
uv run pytest apps/api/tests/test_recon05c_semantic_recall_authority.py packages/domain/tests/test_semantic_recall.py -q
uv run ruff check apps/api/src/personal_enigma/api/storage/semantic_recall.py apps/api/tests/test_recon05c_semantic_recall_authority.py
uv run basedpyright apps/api/src/personal_enigma/api/storage/semantic_recall.py
```
