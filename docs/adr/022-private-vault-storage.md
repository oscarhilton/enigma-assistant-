# ADR-022: Private Vault Storage — Encrypted SQLite, Blob Separation, Data Classification

**Status:** Accepted  
**Date:** 2026-08-17

## Context

[ADR-021](./021-personal-data-security-boundary.md) established the **network / LLM boundary** as a security invariant: select → transform → transmit last, single audited egress gate, email as hostile input. That boundary is necessary but **not sufficient** for a watertight personal-data pilot.

Connecting Oscar's inbox requires specifying the **entire data lifecycle** — ingest, at-rest encryption, retention, derived indexes, logging, backups, and deletion — before claiming the system is secure. The design goal is:

> **Compromise of any one ordinary boundary does not reveal the whole private world.**

This is **not** a claim of impossibility under active malware running as the user. It is an honest tiered model: each layer defends a specific theft or leak vector; no single ordinary failure (stolen locked laptop, copied `~/.enigma/`, leaked backup, compromised remote LLM) should expose wholesale private history.

[ADR-005](./005-demo-private-storage-roots.md) separates Demo, Private, and Shadow storage roots. [ADR-004](./004-notes-best-effort-no-sqlite.md) forbids scraping third-party SQLite and defaults Notes to HIGH privacy. This ADR specifies **Private-mode vault architecture** — layout, keys, classification, retention, and derivative invariants — that SEC-01 must implement before live Gmail sync.

## Decision

### Transitional dual-store architecture (RECON-04A)

Private mode uses **two durable SQLite stores** during the SEC-01 foundation tranche. They are **not merged** in this phase; future unification is deferred.

| Store | Role | Default path | Engine |
| --- | --- | --- | --- |
| **PrivateVault** (this ADR) | Canonical encrypted retained / derived memory | ENIGMA_HOME private vault.db plus blobs and audit dirs | SQLCipher via sqlcipher3 |
| **M00a operational DB** | Ingest / sync / API operational tables (Alembic) | XDG share personal-enigma private.db (unchanged) | Plain SQLite via ENIGMA_DATABASE_URL and apps/api/db |

**Crossover rules (transitional):** PrivateVault does not replace apps/api/db, ENIGMA_DATABASE_URL, or worker open_worker_store(). No migration between stores in RECON-04A.


### Private vault layout

Private mode persists under `~/.enigma/private/` (configurable via `ENIGMA_HOME` / `ENIGMA_PRIVATE_STORAGE_ROOT`). Demo and Shadow use sibling roots per [ADR-005](./005-demo-private-storage-roots.md) and [ADR-008](./008-shadow-storage-roots.md) — never shared DB files, HMAC keys, or blob directories.

```text
~/.enigma/                              # ENIGMA_HOME — app data, NOT ~/Documents / iCloud
├── private/
│   ├── vault.db                        # encrypted SQLite (SQLCipher or equivalent) — structured world model
│   ├── blobs/                          # encrypted raw source blobs (email bodies, MIME, attachments)
│   ├── audit/                          # egress / audit records (encrypted)
│   └── config.json                     # non-secret config only (paths, feature flags, retention prefs)
├── demo/<scenario>/...                 # isolated demo roots
└── shadow/...                          # isolated shadow root
```

**Location rules:**

- `ENIGMA_HOME` defaults to `~/.enigma/` — a dedicated app-data directory, **not** a user Documents folder subject to iCloud sync.
- `config.json` holds **no secrets** (no OAuth tokens, no encryption keys, no API keys).
- Stealing the `private/` directory alone yields **cryptographic garbage** without Keychain material.

### Key hierarchy

```text
OS Keychain (platform secure enclave)
├── OAuth refresh tokens              # Gmail pilot — Keychain ONLY, never vault.db
├── Master key (MK)                   # wraps data keys; never written to disk plaintext
└── Device identity key               # future: signed envelopes, coordination

Master key wraps:
├── DATA KEY    → vault.db (SQLCipher page encryption)
├── BLOB KEY    → blobs/ (per-file AEAD envelopes)
└── AUDIT KEY   → audit/ (egress disclosure records at rest)
```

**Theft tiers:**

| Asset stolen | Effect |
| --- | --- |
| `~/.enigma/private/` only | Unreadable ciphertext — no MK, no OAuth |
| Keychain OAuth refresh only | Ongoing Gmail access — **no** historical vault decryption |
| Keychain MK only | Historical vault decrypt — **no** ongoing Gmail unless OAuth also stolen |
| Both Keychain + `private/` | Full historical + ongoing access — highest tier; requires honest "malware while unlocked" caveat |

OAuth refresh tokens are **never** stored in `vault.db`. This separates **historical data theft** from **ongoing mailbox access** into distinct compromise tiers.

### Data classification model

All persisted and transmitted data is classified before the Gmail pilot lands typed boundaries in code:

| Class | Examples | At-rest | May cross egress gate |
| --- | --- | --- | --- |
| **SECRET** | OAuth refresh, encryption keys, device keys, API keys | Keychain only | Never |
| **PRIVATE_RAW** | Email bodies, attachments, note bodies, calendar descriptions, raw MIME | Encrypted blob store + metadata in vault | Never |
| **PRIVATE_DERIVED** | Obligations, people graph, summaries, embeddings, FTS index, vector index, semantic labels, relations | Encrypted vault **only** | Never (transform first → REMOTE_SAFE) |
| **REMOTE_SAFE** | Pseudonymous transformed context, allowlisted tool schemas | May be ephemeral in memory only | Yes — sole egress payload class |
| **PUBLIC** | Non-personal config, JSON schemas, feature flags | `config.json` plaintext OK | Yes |

**Purpose-scoped subclass (not a sixth egress class):** `PRIVATE_DERIVED_PREFERENCE` names durable **style-enum tone memory** ([ADR-025](./025-tone-memory-how-to-speak-not-who-you-are.md)) — still `PRIVATE_DERIVED` at rest (encrypted vault only), still never egressed as-is. Coarse enums may be projected to `REMOTE_SAFE` for C09. Less sensitive than `PRIVATE_RAW` conversation logs; still personal data. Not a personality dossier.

**Future typed boundaries** (SEC-01 / SEC-02 implementation):

```text
PrivateRaw[T]       — ingest / blob paths only
PrivateDerived[T]   — vault-internal reasoning paths only
RemoteSafe[T]       — sole type accepted by egress_gate.submit()
```

Remote and LLM code paths accept **only** `RemoteSafeContext`. Compile-time or runtime guards reject `PrivateRaw` / `PrivateDerived` at the egress choke point ([SEC-02](../../tickets/security/SEC-02-audited-remote-egress-gate.md)).

### SourceRecord vs world model separation

Raw source content is **not** duplicated across tables. Structured world-model rows reference blobs by id.

**SourceRecord** (in `vault.db`):

| Field | Purpose |
| --- | --- |
| `id` | Internal stable id |
| `source` | e.g. `gmail`, `notes`, `calendar` |
| `external_id` | Provider id (Gmail message id, etc.) |
| `received_at` | Ingest timestamp |
| `content_hash` | Integrity / dedupe fingerprint |
| `blob_ref` | Pointer to encrypted blob file |

**Raw body** lives in `blobs/` as an encrypted envelope — never inline in SQL rows, never duplicated in Obligation/Evidence tables.

Obligation, Evidence, AttentionItem, and similar domain rows reference `source_id` — not embedded body text. Deletion is **blob + references**: remove blob file, null or cascade references, re-index derived material if required.

### Retention & reconstructability boundary

Full specification: [data-retention.md](../architecture/data-retention.md).

**Risk is not megabytes stored.** Approximate risk:

```text
risk ≈ sensitivity × breadth × time depth × cross-linkability × identifiability × accessibility
```

**Red-line test:** If Enigma lost access to all original sources tomorrow, how much of the user's life could be reconstructed from Enigma alone? If **"quite a lot"** → too far. Enigma is **working memory**, not a second permanent archive.

**Persistent shadow shape:** Durable `PRIVATE_DERIVED` memory follows abstract-state rules — opaque IDs, enums, coarse buckets, purpose-scoped graphs — not reconstructive prose. Full specification: [ADR-023](./023-persistent-shadow-abstract-state-not-biography.md). Operational benchmark: [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) · [SEC-05 Q16](../../tickets/security/SEC-05-personal-data-pilot-gate.md).

**Design principle:** Retain **minimum sufficient state**, not maximum available history.

#### Three zones

| Zone | Contains | Stance |
| --- | --- | --- |
| **Green** | Current commitments, minimal contact identities, upcoming calendar, recent source evidence | Purposeful working state |
| **Amber** | Months of raw email, full social graph, historic messages, embeddings, inferred preferences | Strong justification + expiry |
| **Red** | Permanent mailbox archive + location + health + finance + attachments + behavioural inferences cross-linked indefinitely | Shadow copy of person — **avoid** |

#### Four-layer lifecycle (canonical)

Full model: [data-retention.md](../architecture/data-retention.md) · [ADR-023](./023-persistent-shadow-abstract-state-not-biography.md).

```text
SOURCE WORLD          raw · identifiable · short-lived (PRIVATE_RAW blobs)
       ↓ extract
ACTIVE PRIVATE STATE  purpose-bound — only what Enigma currently needs (PRIVATE_DERIVED)
       ↓ decay / abstract
PSEUDONYMOUS SHADOW   enums · buckets · state transitions · low narrative reconstructability
       ↓ expiry
FORGET                recoverability → zero within Enigma
```

**DECAY ≠ FORGET:** DECAY reduces detail, precision, and linkability while retaining utility. FORGET is terminal — recoverability → zero. "Forget this person" must **not** mean rename-to-`PERSON_Q7` and keep the graph forever.

Shadow/meaning records carry lightweight **lineage** for deterministic forget:

```yaml
derived_from: [SRC_123, SRC_188]
purpose: OPEN_LOOP_TRACKING
retention_class: ACTIVE_UNTIL_RESOLVED
expires_after_resolution: 30d
```

`forget(SRC_123)` is a **graph operation**: what depends exclusively on this source? what has independent evidence? what must disappear? what can remain but lose confidence?

#### Memory decay model (summary)

```text
incoming evidence → SOURCE WORLD (RAW — high detail, short lifetime)
                 → ACTIVE PRIVATE STATE (purpose-bound structured facts)
                 → PSEUDONYMOUS SHADOW (abstract enums/buckets — low reconstructability)
                 → FORGET (recoverability → zero)
```

Pilot bias: **deliberately too aggressive on forgetting** — extend TTLs when proven necessary, do not shrink later.

> **No retained derivative may outlive its justification merely because it is derived.**

Applies to embeddings, interaction-frequency aggregates, inferred relations, cached retrieval chunks, source-derived features, historical audit material. **"Delete raw data" alone is NOT successful forgetting.**

#### Sensitive inferences (special class)

Do **not** infer-and-store permanently: medical, sexuality, political, substance, intimate relationships, financial distress, behavioural routines. Temporary relevance for answering is OK; persistent sensitive memory needs higher bar / user approval. **Derived data can be more sensitive than originals** — deletion must cascade to derived state, not just raw bodies.

#### User forget operations (future first-class)

- "What do you remember about me?"
- "Why are you remembering that?"
- "Forget everything about that project/person/before June"

Product principle: **The safest Enigma isn't the one that can remember everything. It's the one that knows what is worth forgetting.**

### Retention policy (pilot defaults; user-configurable)

"Store everything forever" is **not** the default. Gmail remains archive of record.

| Data | Default retention | Zone | Notes |
| --- | --- | --- | --- |
| OAuth refresh | Persistent (Keychain) | Green | SECRET — Keychain only |
| Raw email body (blob) | **7 day** cache max (pilot) | Amber | Re-fetch on miss; no indefinite |
| Attachments | Do not persist by default | Amber | Lazy fetch; delete temp after parse |
| Active obligations | While relevant | Green | Open / blocking |
| Resolved obligations | **30–90 days** then discard/compress | Green → Amber | Minimal audit stub optional |
| Calendar | Limited recent horizon | Green | Upcoming + short past window |
| People / contacts | Identity + alias + minimal relationship state | Green | **Not** full correspondence history |
| Canonical facts / evidence ids / hashes | While relevant | Green | Structural memory without full body |
| Embeddings / FTS / vector index | **Expire with source** | Amber | Reproducible, not precious; always inside vault |
| Remote LLM payloads | No content persistence | — | Hash / counts / audit only ([SEC-02](../../tickets/security/SEC-02-audited-remote-egress-gate.md)) |
| Egress disclosure records | Per audit policy | Green | Hashes and field summaries only |

User-configurable retention per class in non-secret `config.json`. `PRIVATE_DERIVED` rows follow domain relevance rules and [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md) GC / forget cascade.

### Derivative invariants (embeddings / indexes paranoia)

> **No private derivative may be persisted outside the encrypted vault.**

Embeddings, vector indexes, FTS tables, summaries, and semantic labels are **PRIVATE_DERIVED**. They live inside SQLCipher-protected `vault.db` (or blob envelopes under the same key hierarchy) — never in a sibling plaintext file.

> **No retained derivative may outlive its justification merely because it is derived.**

Derivatives carry **lineage** (`derived_from`, `purpose`, `retention_class`, `expires_after_resolution`) so `forget(source_id)` cascades deterministically — not best-effort blob delete. See [data-retention.md — Lineage schema](../architecture/data-retention.md#lineage-schema).

**Forbidden pattern:** `vault.db` encrypted + `vectors.db` plaintext.  
**Required pattern:** single encrypted vault (or encrypted blob per index shard) under `DATA KEY`.

Local retrieval and semantic search operate on decrypted pages **in process memory only** — not exported to unencrypted sidecar stores.

### Attachments

1. **Lazy fetch** — download attachment bytes only when a tool or pipeline step requires them.
2. **Temp private location** — parse in an isolated temp dir under `private/` or OS temp with restrictive permissions.
3. **Parse isolated** — attachment parsers are **on the threat model** (attacker-controlled files); no parser execution in LLM context.
4. **Encrypt retained or delete** — if retention is required, encrypt under `BLOB KEY` and store in `blobs/`; otherwise secure-delete temp files after parse.

### Logging rules

Production logging is **redaction-first**:

| Allowed | Forbidden (unless explicit dev switch) |
| --- | --- |
| Internal ids, correlation ids | Email bodies, subject lines (unless classified safe) |
| Content hashes, payload hashes | OAuth tokens, API keys, refresh tokens |
| Timings, reason codes, gate decisions | Raw LLM prompts, tool results with private text |
| Allowlisted field names in disclosure summaries | Attachment bytes, pseudonym maps, `PrivatePerson` fields |

A **`ENIGMA_DEBUG_RAW_LOGGING=1`** (or equivalent) dev switch is required for raw debugging — never default-on in Private pilot builds.

### Backups

- **No accidental export** — no implicit JSON dumps, no iCloud-synced directories, no "export all mail" without explicit user action.
- **Explicit encrypted export only** — backup is a deliberate operator action producing an encrypted archive (MK-wrapped or passphrase-protected); documented in SEC-01 runbook.
- Backup behaviour is **opt-in and documented** — default install does not sync Private data to cloud storage.

### Threat tiers (explicit limits)

| Scenario | Primary defences | Honest limit |
| --- | --- | --- |
| Laptop stolen, disk locked | FileVault / OS full-disk encryption + vault encryption | Unlocked session + captured MK in memory |
| `~/.enigma/private/` copied | SQLCipher + blob AEAD — useless without Keychain MK | MK extracted while app unlocked |
| Backup leaked | Encrypted export only — useless without backup passphrase / MK | Weak user passphrase |
| Remote LLM / Fireworks compromised | Privacy transform + egress allowlist — receives REMOTE_SAFE only | Transform bug sends disallowed field until gate catches |
| Malicious email | Untrusted input policy + no credential tools + adversarial tests ([SEC-03](../../tickets/security/SEC-03-untrusted-content-adversarial-tests.md)) | Logic bug treats injection as instruction |
| OAuth token stolen (Keychain) | Keychain separation — ongoing access, not historical vault | Attacker with Keychain + network |
| Active malware while unlocked | MK and OAuth in process memory — **much harder, not impossible** | Full user-session compromise out of scope for "ordinary boundary" claim |

## Consequences

- SEC-01 implements this layout before SEC-04 connects live Gmail.
- SEC-02 egress gate enforces **REMOTE_SAFE only** — typed boundary at the gate module.
- SEC-05 gate checklist includes precise PASS/FAIL answers for each storage lifecycle question ([SEC-05](../../tickets/security/SEC-05-personal-data-pilot-gate.md)).
- Demo Mode continues isolated roots ([ADR-005](./005-demo-private-storage-roots.md)); demo may use simplified storage for evaluation but must not share keys or paths with Private.
- Notes ingestion respects [ADR-004](./004-notes-best-effort-no-sqlite.md): no Apple Notes SQLite scraping; note bodies classified PRIVATE_RAW at rest.
- Vector / embedding packages must not create plaintext sidecar DBs under Private roots.

## Related

- [ADR-021 — Personal data security boundary](./021-personal-data-security-boundary.md)
- [ADR-004 — Notes best-effort; no SQLite scraping](./004-notes-best-effort-no-sqlite.md)
- [ADR-005 — Demo vs Private storage roots](./005-demo-private-storage-roots.md)
- [ADR-008 — Shadow storage roots](./008-shadow-storage-roots.md)
- [personal-data-security.md](../architecture/personal-data-security.md)
- [data-retention.md](../architecture/data-retention.md)
- [tickets/security/SEC-01](../../tickets/security/SEC-01-secrets-encrypted-storage.md)
- [tickets/security/SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md)
- [tickets/security/SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md)
- [tickets/security/SEC-02](../../tickets/security/SEC-02-audited-remote-egress-gate.md)
- [tickets/security/SEC-05](../../tickets/security/SEC-05-personal-data-pilot-gate.md)
- [ADR-023 — Persistent shadow](./023-persistent-shadow-abstract-state-not-biography.md)
- [ADR-025 — Tone memory](./025-tone-memory-how-to-speak-not-who-you-are.md) · [tone-memory.md](../architecture/tone-memory.md) — `PRIVATE_DERIVED_PREFERENCE` subclass; how to speak, not who you are
