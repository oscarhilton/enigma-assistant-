# SEC-01 — Secrets + local encrypted storage

**Status:** done  
**Branch:** `ticket/SEC01-secrets-encrypted-storage`  
**Domain:** security  
**May edit:** `apps/api/src/personal_enigma/api/storage/**`, `packages/privacy/**` (local-at-rest helpers only), `apps/web` (settings surfaces for storage status), `apps/api/tests/**`, `packages/privacy/tests/**`  
**Must not edit:** `packages/ingestion/.../sources/gmail.py` (SEC-04), demo simulation roots, Shadow storage

**Hard depends:** [SEC-00](./SEC-00-personal-data-threat-model.md)  
**Soft (~):** [M00a](../platform/) (persist sync state), [ADR-008](../../docs/adr/008-shadow-storage-roots.md)

## Goal

Establish **Keychain-backed OAuth token storage**, **Private vault layout** ([ADR-022](../../docs/adr/022-private-vault-storage.md)), encrypted at-rest storage for all classified data, and **redaction-first logging** before any live Gmail sync.

**SEC-06 is the co-equal other half of this ticket.** SEC-01 protects what is retained (encryption, keys, vault layout); [SEC-06](./SEC-06-retention-memory-decay-forget.md) controls whether data should exist at all (retention, decay, forget). Neither alone is sufficient for the storage plane.

## Architectural reference

[ADR-022 — Private vault storage](../../docs/adr/022-private-vault-storage.md)

## Deliverables

### Vault layout (`~/.enigma/private/`)

- [x] `ENIGMA_HOME` defaults to `~/.enigma/` — dedicated app data, **not** `~/Documents` or iCloud-synced folders
- [x] Private root structure:
  ```text
  ~/.enigma/private/
      vault.db          # SQLCipher (or equivalent encrypted SQLite)
      blobs/            # encrypted raw source blobs (PRIVATE_RAW)
      audit/            # encrypted egress/audit records
      config.json       # non-secret config only (PUBLIC)
  ```
- [x] Demo / Shadow use sibling roots per [ADR-005](../../docs/adr/005-demo-private-storage-roots.md) / [ADR-008](../../docs/adr/008-shadow-storage-roots.md) — no shared DB, keys, or blob dirs

### Key hierarchy

- [x] **OS Keychain** holds: OAuth refresh tokens, Master key (MK), device identity key
- [x] MK wraps: **DATA KEY** (`vault.db`), **BLOB KEY** (`blobs/`), **AUDIT KEY** (`audit/`)
- [x] Stealing `~/.enigma/private/` without Keychain → unreadable ciphertext (verified by test)
- [x] OAuth refresh tokens **Keychain-only** — never in `vault.db`, env files, git, or LLM context
- [ ] API keys for remote inference separate from Google OAuth; Keychain or secure env injection only

### Secrets hygiene

- [ ] Dedicated **Google Cloud project** for Enigma pilot documented in setup; client id/secret in Keychain or secure config — not committed
- [x] Token refresh path audited; refresh tokens never logged (`safe_logging` redaction helpers)

### SourceRecord + blob separation

- [x] `SourceRecord` table: `id`, `source`, `external_id`, `received_at`, `content_hash`, `blob_ref`
- [x] Raw email body in encrypted blob — **not** inline in SQL, **not** duplicated in Obligation/Evidence rows
- [x] Deletion API: remove blob + cascade/null references sanely

### Retention & reconstructability (per data class)

Architectural reference: [data-retention.md](../../docs/architecture/data-retention.md) · [ADR-022 retention section](../../docs/adr/022-private-vault-storage.md#retention--reconstructability-boundary).

**Red-line test:** If Enigma lost all original sources tomorrow, could someone reconstruct "quite a lot" of the user's life from Enigma alone? Retention policy must keep the answer **no**.

Pilot defaults (aggressive; user-configurable in `config.json`):

| Data class | Classification | Default TTL | Enforcement |
| --- | --- | --- | --- |
| OAuth refresh | SECRET | Persistent (Keychain) | Keychain-only |
| Raw email body blob | PRIVATE_RAW | **7 day** max (pilot) | Blob GC job; Gmail = archive of record |
| Attachments | PRIVATE_RAW | **Do not persist** | Lazy fetch; secure-delete temp |
| Active obligations | PRIVATE_DERIVED | While relevant | Domain relevance |
| Resolved obligations | PRIVATE_DERIVED | **30–90 days** then discard/compress | GC + optional minimal audit stub |
| Calendar | PRIVATE_RAW / DERIVED | Limited recent horizon | Horizon GC |
| People / contacts | PRIVATE_DERIVED | Identity + alias + minimal relationship state | **Not** full correspondence history |
| Embeddings / FTS / vector index | PRIVATE_DERIVED | **Expire with source** | Cascade delete when SourceRecord / blob expires; re-embed on re-fetch |
| Remote LLM payloads | — | **No content persistence** | SEC-02 audit: hash / counts only |

- [ ] Per-class retention documented in `config.json` schema + operator runbook
- [ ] Raw email body blob: **7 day** default (pilot); not indefinite; Gmail documented as archive of record
- [ ] Attachments: lazy fetch; secure-delete after parse unless explicitly retained
- [ ] Resolved obligations: 30–90 day post-resolution GC
- [ ] Embeddings / FTS / vectors: **expire with source** — deletion of blob or SourceRecord triggers index row removal; no orphaned vectors
- [ ] "Store everything forever" **not** the default
- [x] Retention prefs in non-secret `config.json`; enforcement in blob GC + derived GC jobs *(prefs schema only — enforcement is SEC-06)*
- [ ] **No permanent pilot storage** of sensitive inference classes (medical, sexuality, political, substance, intimate, financial distress, behavioural routines)
- [ ] Deletion API cascades to **derived state** (summaries, embeddings, graph edges) — not just raw blobs

Full memory decay + forget operations: [SEC-06](./SEC-06-retention-memory-decay-forget.md).

### Derivative invariants

- [x] Embeddings, FTS, vector index, summaries, semantic labels = **PRIVATE_DERIVED** inside encrypted `vault.db` *(vault API — `touch_structured_row`; embeddings package wiring deferred)*
- [ ] **No private derivative persisted outside encrypted vault** — no plaintext `vectors.db` sidecar
- [ ] `packages/embeddings` and retrieval code must not create unencrypted index files under Private roots
- [ ] **No retained derivative may outlive its justification merely because it is derived** — lineage fields on derived rows ([SEC-06](./SEC-06-retention-memory-decay-forget.md))
- [ ] Deletion / expiry cascades to **all derivative classes**: embeddings, FTS, vectors, summaries, interaction-frequency aggregates, inferred relations, cached retrieval chunks, source-derived features, historical audit material tied to scope

### Attachments

- [ ] Lazy fetch only when needed
- [ ] Parse in isolated temp location; parsers treated as untrusted input ([SEC-00](./SEC-00-personal-data-threat-model.md))
- [ ] Encrypt retained blobs under BLOB KEY or secure-delete after parse

### Safe logging

- [x] Production: ids, hashes, timings, reason codes only — no bodies, subject lines (unless safe), tokens, raw prompts, attachments, pseudonym maps
- [x] `ENIGMA_DEBUG_RAW_LOGGING=1` (or equivalent) dev switch required for raw debugging — off by default in Private pilot
- [ ] CI invariant or lint rule flagging obvious secret patterns in log calls (soft)

### Backups

- [ ] Documented operator runbook: explicit **encrypted export only** — no accidental JSON dumps
- [ ] No iCloud sync of `ENIGMA_HOME`; backup behaviour deliberate and opt-in
- [ ] Migration story documented (even if v0 is manual export/import)

## Acceptance criteria

- [x] OAuth connect flow persists tokens to Keychain only; grep of repo and default log dir finds no live tokens in tests *(OAuthTokenStore + stolen-dir / oauth tests; live connect flow is SEC-04)*
- [x] Raw mail round-trip: ingest stub → SourceRecord + encrypted blob → read back locally; ciphertext at rest verifiable
- [x] Copying `private/` without Keychain MK → decrypt fails
- [x] OAuth refresh token absent from `vault.db` (schema + runtime assertion)
- [ ] Embeddings/FTS test writes only inside SQLCipher vault — no plaintext sidecar files
- [x] `RemoteInferenceConfig(enabled=False)` still allows local ingest + transform tests *(unchanged — no regression)*
- [ ] Documented operator setup for dedicated GCP project + readonly scope request
- [ ] Retention GC removes expired blobs, cascades embeddings/indexes tied to expired sources, and updates references
- [ ] Embedding expiry test: delete SourceRecord → no orphaned vector/FTS rows

## Test plan

- [x] Unit tests for encrypt/decrypt envelope (SQLCipher config smoke)
- [x] Keychain adapter tests with mock / CI skip on non-macOS (`ENIGMA_KEYCHAIN_BACKEND=memory`)
- [x] SourceRecord + blob round-trip and deletion cascade
- [ ] Derivative invariant test: embedding write produces no plaintext files under `private/`
- [x] Log redaction regression test with fixture payload containing fake token + email body
- [x] "Stolen dir" test: copy vault files to temp dir, attempt open without Keychain → fail

## Privacy constraints

- Raw email **local-only** invariant enforced at storage layer
- Classification types enforced at storage API boundary ([ADR-022](../../docs/adr/022-private-vault-storage.md))
- No wholesale export APIs without separate ticket

**Unlocks:** SEC-02, SEC-04, SEC-06 (co-equal retention half)

## Related ADR

[ADR-021](../../docs/adr/021-personal-data-security-boundary.md) · [ADR-022](../../docs/adr/022-private-vault-storage.md) · [SEC-06](./SEC-06-retention-memory-decay-forget.md) (co-equal half) · [data-retention.md](../../docs/architecture/data-retention.md) · [ADR-004](../../docs/adr/004-notes-best-effort-no-sqlite.md) · [ADR-005](../../docs/adr/005-demo-private-storage-roots.md)
