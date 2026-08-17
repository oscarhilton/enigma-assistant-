# SEC-04 — Real external source through private architecture (Gmail readonly)

**Status:** in-progress (implementation landed; live TEST account smoke pending)  
**Branch:** `ticket/SEC04-gmail-readonly-connector`  
**Domain:** security · google  
**May edit:** `packages/ingestion/src/personal_enigma/ingestion/sources/gmail.py`, `packages/ingestion/src/personal_enigma/ingestion/gmail_persistence.py`, `packages/fixtures/src/personal_enigma/fixtures/nasty_mailbox_manifest.py`, `packages/ingestion/tests/fixtures/gmail/nasty/**`, `apps/api/src/personal_enigma/api/google/gmail/**`, `apps/worker/src/personal_enigma/worker/google/gmail/**`, `apps/api/tests/**`, `packages/ingestion/tests/**`, `packages/fixtures/tests/**`  
**Must not edit:** Demo simulation sources, Shadow roots, orchestrator policy, egress gate core (SEC-02)

**Hard depends:** [SEC-01](./SEC-01-secrets-encrypted-storage.md), [SEC-02](./SEC-02-audited-remote-egress-gate.md), [SEC-03](./SEC-03-untrusted-content-adversarial-tests.md)  
**Soft (~):** [M11](../google/M11-gmail.md) (scaffold), [M10](../google/) (Contacts identity)

## Goal

**Prove a real external source enters without bypassing the private architecture** — not "connect Gmail" or wire Oscar's inbox.

Success = a **synthetic nasty test mailbox** on a **Google TEST account** survives the **full path** end-to-end. Oscar's inbox remains blocked until [SEC-05](./SEC-05-personal-data-pilot-gate.md) PASS.

## Hard precondition (cannot PASS without)

When `persistence_backend == legacy_plaintext` (legacy `private.db` / `personal_enigma.api.db`), the Gmail adapter **must refuse init/sync** — **no warning, fallback, or dev exception** during SEC-04 evaluation.

**Guard (landed):** `packages/ingestion/src/personal_enigma/ingestion/gmail_persistence.py` — `PersistenceBackend.LEGACY_PLAINTEXT` vs `ENCRYPTED_VAULT`; `assert_gmail_encrypted_vault_persistence()` from `GmailSource` (when `enforce_encrypted_vault=True`) and `run_gmail_sync()`. Tests: `packages/ingestion/tests/test_gmail_persistence_guard.py`.

Real email bodies must never land in plaintext SQLite. SEC-04 writes only to encrypted vault (`SourceRecord` + blobs).

## Pipeline (SEC-04 scope)

```text
gmail.readonly
  → hostile MIME / HTML / attachment boundary (real parser path)
  → canonical private record (SourceRecord)
  → encrypted vault only (vault.db + blobs/)
  → world-model extraction / transform
  → SEC-02 egress gate
```

LLM and tools never call `gmail.users.messages.send`, `modify`, or `trash`.

## Nasty mailbox matrix (acceptance + fixture manifest)

Canonical manifest: [`nasty_mailbox_manifest.py`](../../packages/fixtures/src/personal_enigma/fixtures/nasty_mailbox_manifest.py)  
Gmail API JSON stubs: `packages/ingestion/tests/fixtures/gmail/nasty/`  
SEC-03 adversarial corpus: [`adversarial_email_cases.py`](../../packages/fixtures/src/personal_enigma/fixtures/adversarial_email_cases.py)  
Canary secrets: [`alex_sensitive_canaries.py`](../../packages/fixtures/src/personal_enigma/fixtures/alex_sensitive_canaries.py)

| Category | Representative fixture |
| --- | --- |
| **plain-text injection** | `inj-ignore-previous-instructions`, `inj-tool-call-forgery`, `inj-credential-phish` |
| **HTML-hidden injection** | `inj-html-hidden-text` |
| **quoted/reply content** | `nasty-quoted-reply` (Gmail JSON) |
| **multipart MIME** | `inj-multipart-plain-html` |
| **malicious attachment metadata** | `nasty-malicious-attachment-metadata` (Gmail JSON) |
| **fake system instructions** | `inj-system-prompt-leak` |
| **embedded URLs/tracking** | `nasty-embedded-urls-tracking` (Gmail JSON) |
| **oversized/malformed bodies** | `nasty-oversized-malformed-body` (Gmail JSON) |
| **canary secrets** | all `ALEX_SENSITIVE_CANARIES` rows |

Every matrix row must PASS through the full pipeline on the TEST account (recorded fixtures for CI; live smoke optional).

## Milestone target

- **Google TEST account** + synthetic nasty mailbox seeded from manifest (**NOT Oscar's inbox**)
- Hostile HTML/MIME through **real parser path** (not Alex demo shortcut alone)
- **Encrypted vault only** — `persistence_backend == legacy_plaintext` → hard refuse
- **SEC-03 adversarial cases survive real ingestion path** — re-run through Gmail adapter + vault
- **Disclosure visible** — exact privacy disclosure via egress panel (SEC-02)
- **`gmail.readonly` only** — no write scopes

## Deliverables

- [x] Legacy persistence guard (`persistence_backend == legacy_plaintext` → refuse) + assertion tests
- [x] Nasty mailbox fixture manifest + manifest regression tests
- [x] Gmail API JSON fixtures for matrix rows marked `gmail_api_json` (quoted reply, attachment metadata, URLs, oversized/malformed)
- [x] OAuth scope locked to `https://www.googleapis.com/auth/gmail.readonly` — reject consent if broader scopes returned
- [ ] Dedicated Google Cloud project documented in operator runbook (SEC-01)
- [ ] Tokens from Keychain (SEC-01); sync worker writes to encrypted Private vault only
- [x] MIME/HTML/attachment boundary — real parser; attachments lazy-fetch; no plaintext spill
- [x] `DataSource.get_changes` incremental sync with safe logging (no body dumps)
- [ ] Entity resolution via Contacts when available (M10 soft)
- [x] Feature flag or env gate: `ENIGMA_GMAIL_LIVE=1` required for real sync — default off
- [x] Explicit separation from Demo Mode DB ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))

## Non-goals

- **Oscar's inbox** (blocked until SEC-05 PASS)
- **OAuth implementation in this documentation slice** — scope audit + Keychain wiring land with connector implementation; no live OAuth in SEC-04 eval CI
- Send, draft, label modify, delete
- `gmail.metadata`-only shortcut that hides bodies if product needs bodies locally (document choice)
- IMAP / Mail.app
- Autonomous triage or reply
- Migrating or reading legacy `private.db`
- [C10](../conversational-ui/C10-cortex-brain-visualizer.md) cortex wiring — **deferred** (observability candy after SEC-02/SEC-03 audit vocabulary stabilises)

## Acceptance criteria

- [x] **Legacy store guard:** `persistence_backend == legacy_plaintext` → Gmail connector / sync entry refuses init — no fallback or dev exception (`test_gmail_persistence_guard.py`)
- [x] **Nasty mailbox manifest:** all matrix categories present with resolvable fixture refs (`test_nasty_mailbox_manifest.py`)
- [x] **Synthetic nasty test mailbox:** Google TEST account corpus ingested through real parser path into encrypted vault only (CI: `GmailFixtureTransport` + `test_sec04_gmail_ingestion.py`)
- [x] **SEC-03 survival:** adversarial email cases re-run green through **real ingestion path** (not Alex demo shortcut)
- [x] **No writes possible:** scope audit test — connector code contains no send/modify API method calls; OAuth locked to `gmail.readonly`
- [x] **Exact privacy disclosure:** egress panel shows what left the machine for any LLM path touching ingested mail (SEC-02 integration)
- [x] Recorded HTTP fixture tests still pass; live smoke on TEST account optional
- [x] Ingest + local transform works with remote inference disabled
- [x] Raw MIME never appears in egress gate disclosure records

## Test plan

- Legacy persistence refusal unit tests (`test_gmail_persistence_guard.py`)
- Nasty mailbox manifest regression (`test_nasty_mailbox_manifest.py`)
- Recorded Gmail API fixtures (M11 + `gmail/nasty/` matrix)
- Scope-enforcement unit test
- Synthetic nasty mailbox integration (TEST account)
- SEC-03 adversarial corpus through real ingestion path
- Privacy invariants on transformed email snippets
- Egress disclosure integration test

## Privacy constraints

- Medium default privacy level; strip secrets before any remote path
- Mail content tagged **untrusted** in metadata for downstream consumers

**Unlocks:** SEC-05 (after SEC-06, SEC-07)

## Related ADR

[ADR-021](../../docs/adr/021-personal-data-security-boundary.md)

**Note on M11:** M11 landed read-only ingestion scaffolding with fixtures. SEC-04 is the **pilot-hardened full pipeline** for Private encrypted vault — not a duplicate M11 ticket.

**Note on C10:** Cortex brain visualizer remains **deferred** — resume after SEC-04 pipeline + SEC-02 audit semantics stabilise; not a SEC-04 blocker.
