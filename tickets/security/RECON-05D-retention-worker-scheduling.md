# RECON-05D — Retained-assertion TTL / forget worker scheduling

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `cursor/recon-05d-retention-worker-scheduling-60d2` (relay; intended `ticket/recon-05d-retention-worker-scheduling`) |
| Domain | `security` / worker jobs |
| ADR | [ADR-022](../../docs/adr/022-private-vault-storage.md) · [ADR-036](../../docs/adr/036-retention-gate-life-memory.md) |

## Package boundary (hard)

- May edit: `apps/worker/src/personal_enigma/worker/retention/**`
- May edit: `apps/worker/src/personal_enigma/worker/main.py`
- May edit: `apps/worker/src/personal_enigma/worker/__init__.py`
- May add: `apps/worker/tests/test_retention_*.py`
- May edit: `tickets/security/RECON-05D-retention-worker-scheduling.md`
- May edit: `docs/architecture/data-retention.md` (worker expiry-path pointer only)
- Must not edit: `apps/api/src/personal_enigma/api/storage/retention_vault.py`, `retention_forget.py`, `memory_inventory.py`, `vault.py`, `forget.py`, `gc.py`
- Must not edit: embeddings, HTTP forget routes, UI, C28, life scripts, kernel/router, semantic-recall authority, donor SEC-06 GC semantics

## Hard depends

- RECON-04 SEC-06 vault foundation (landed on `main`)
- RECON-05A retention → vault adapter (landed on `main`)
- RECON-05B forget / TTL / inventory (landed on `main`)

## Soft depends (~)

- C29 / C15 donor worker `retention/gc.py` — inspect only; do not re-port vault internals

## Goal

Wire **worker-side scheduling / orchestration** so retained-assertion TTL expiry and forget maintenance run through the canonical vault APIs already on `main`:

```text
worker job
  → PrivateVault.open(...)
  → VaultDurableAssertionStore.expire_ttl() | .forget()
  → RECON-05B cascade (unchanged)
```

Preserve the ingest / Alembic operational store. This job uses **PrivateVault** on purpose and must not change `ENIGMA_DATABASE_URL` / `open_worker_store()` semantics.

## Donor delta

C29 / C15 `run_retention_gc` opened `PrivateVault` and called `vault.run_gc()` (SEC-06 raw-blob + resolved-obligation sweep). That API already lives on `main` via RECON-04 and is **not** the retained-assertion TTL path.

This tranche adapts the donor shape (thin worker job + vault open) to current worker architecture:

| Donor | This tranche |
| --- | --- |
| `run_retention_gc` → `PrivateVault.run_gc()` | `run_retained_assertion_ttl_expiry` → `VaultDurableAssertionStore.expire_ttl` |
| no explicit forget job | `run_retained_assertion_forget` → `VaultDurableAssertionStore.forget` |
| no due-check | `run_due_retention_maintenance` (in-process interval; last-run is caller-supplied) |
| no operational-store warning | PrivateVault only; `ENIGMA_DATABASE_URL` untouched |

Do **not** reimplement forget / TTL / inventory. Do **not** schedule SEC-06 blob GC here.

## Non-goals

- Semantic recall authority / embeddings
- HTTP forget routes / UI / C28 / life scripts / kernel / router
- Replacing RECON-04 `run_gc` or RECON-05B cascade
- Changing Alembic / `ENIGMA_DATABASE_URL` / `open_worker_store()`
- Persisting last-run into the operational DB
- Cryptographic page shredding

## Acceptance criteria

- [x] Worker job opens `PrivateVault` and calls `VaultDurableAssertionStore.expire_ttl`
- [x] Worker can invoke canonical `forget` for a retained assertion id (ids-only result)
- [x] Due-check scheduler runs TTL expiry when due and skips when not
- [x] Operational store / `ENIGMA_DATABASE_URL` is not opened or mutated
- [x] Results log ids / counts only — no assertion payloads or source bodies
- [x] Focused worker tests cover TTL, forget, due-check, and store isolation
- [x] Ticket documents the C29/C15 donor delta

## Test plan

```bash
uv run pytest apps/worker/tests/test_retention_maintenance.py -q
uv run pytest -q
uv run ruff check .
uv run basedpyright apps/worker/src/personal_enigma/worker/retention apps/worker/src/personal_enigma/worker/main.py
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
```

## Privacy constraints

- Forget / TTL results may include assertion ids, derived ids, audit ids, and trigger labels only
- Never log retained payloads, email bodies, or attendee addresses
- Cloud / CI uses `ENIGMA_KEYCHAIN_BACKEND=memory` and a temp vault root — no real Private storage
