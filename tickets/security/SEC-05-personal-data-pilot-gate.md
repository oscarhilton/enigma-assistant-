# SEC-05 — Personal-data pilot gate (hard PASS checklist)

**Status:** todo  
**Branch:** `ticket/SEC05-personal-data-pilot-gate`  
**Domain:** security (gate / documentation + verification)  
**May edit:** `tickets/security/**`, `docs/architecture/personal-data-security.md`, `docs/architecture/data-retention.md`, `docs/adr/021-personal-data-security-boundary.md`, `docs/adr/022-private-vault-storage.md`, `packages/evaluation/**` (gate runner), `docs/architecture/overview.md`  
**Must not edit:** Product features beyond gate verification scripts

**Hard depends:** [SEC-00](./SEC-00-personal-data-threat-model.md), [SEC-01](./SEC-01-secrets-encrypted-storage.md), [SEC-02](./SEC-02-audited-remote-egress-gate.md), [SEC-03](./SEC-03-untrusted-content-adversarial-tests.md), [SEC-04](./SEC-04-gmail-readonly-connector.md), [SEC-06](./SEC-06-retention-memory-decay-forget.md), [SEC-07](./SEC-07-shadow-reconstruction-benchmark.md)

## Goal

**Hard PASS gate** before connecting Oscar's inbox. Any FAIL blocks live Gmail OAuth on Private roots. This is not a vibes review.

Each lifecycle gate question below requires a **precise, falsifiable answer** — not "probably" or "should". Evidence: test name, CI job, or doc section with file path.

## Gate verdict — three separate PASSes

Before Oscar's inbox connects, SEC-05 requires **three independent dimension PASSes**. This is not a composite score, weighted average, or "mostly good" review — each dimension is evaluated separately and must PASS on its own.

| # | Dimension PASS | Required for unlock |
| --- | --- | --- |
| 1 | **Confidentiality PASS** | ✓ |
| 2 | **Minimisation PASS** | ✓ |
| 3 | **Reconstructability PASS** | ✓ |

**Gate rule:**

- Each dimension PASSes **only if every** mapped question (Q1–Q16) and mapped checklist item for that dimension PASSes.
- **Any single dimension FAIL → gate FAIL**, even if the other two dimensions PASS.
- Q4 spans Confidentiality and Minimisation — both halves must PASS for Q4 to PASS; a FAIL on either half fails **both** affected dimensions.

> **Database encrypted ≠ safe.** SQLCipher on `vault.db` and AEAD on `blobs/` answer Confidentiality questions about at-rest ciphertext. Encryption does **not** satisfy Minimisation (did we retain more than we need?) or Reconstructability (does retained structure still rebuild a biography?). A fully encrypted vault that retains indefinite raw bodies, orphaned derivatives, prose-shaped shadow rows, and a global identity graph is a **gate FAIL** — Confidentiality may PASS while Minimisation and Reconstructability FAIL catastrophically.

### Canonical dimension → question mapping

| Dimension | Core question | Questions | Primary evidence |
| --- | --- | --- | --- |
| **Confidentiality** | Can retained data be read if storage is stolen? | Q1, Q3, Q4 (wire/backup/log half), Q5, Q6, Q8, Q9, Q10 | SEC-01, SEC-02, SEC-03 |
| **Minimisation** | Did Enigma retain more than it needs? | Q2, Q4 (backup/log retention half), Q7, Q12, Q13, Q14, Q15 | SEC-01, SEC-06, [data-retention.md](../../docs/architecture/data-retention.md) |
| **Reconstructability** | Can the retained structure rebuild a biography? | Q11, Q16 | SEC-06, SEC-07, [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md) |

---

## 1. Confidentiality PASS

**Question:** Can retained data be read if storage is stolen?

**Fail modes:** Encrypted vault but keys leaked; raw body on wire; stolen dir yields usable plaintext; adversarial email exfiltrates private content; tool auto-execution without approval.

### Maps to

| Theme | Gate evidence |
| --- | --- |
| Encryption at rest | SQLCipher `vault.db`; AEAD `blobs/`; BLOB KEY wrapped by MK |
| Keychain separation | MK, OAuth refresh, device identity **never** in `vault.db` or copied files |
| Stolen-dir test | `~/.enigma/private/` copied without Keychain → cryptographic garbage (Q9) |
| Egress doesn't leak raw | Single audited gate; PRIVATE_RAW rejected; wire capture grep (Q6) |
| Backups / logs / egress disclosure | Encrypted export only; production logs = ids/hashes/reason codes (Q4) |
| Adversarial injection can't exfiltrate | SEC-03 corpus; no auto-execute; no credential exfil to LLM (Q5, Q10) |
| No plaintext derivative sidecars | Embeddings / FTS / vectors inside SQLCipher only (Q3) |
| Threat-tier honesty | FDE + vault encryption; unlocked-session / malware limits documented (Q8) |

### Mapped questions

**Q1, Q3, Q4** (confidentiality half: wire, backup, log), **Q5, Q6, Q8, Q9, Q10**

### Dimension PASS criteria

- [ ] **Confidentiality dimension PASS** — ALL mapped questions PASS with one-paragraph precise answers recorded
- [ ] ALL Confidentiality-mapped checklist items below PASS with evidence links

| Question | PASS requires |
| --- | --- |
| **Q1** | `blobs/` + BLOB KEY wrapped by MK in Keychain; only Enigma Core ingest/retrieve paths decrypt; body never in `vault.db` inline |
| **Q3** | If embeddings / FTS / vector indexes exist: PRIVATE_DERIVED inside SQLCipher `vault.db` only; **no plaintext sidecar**; test proves no `vectors.db` under `private/` |
| **Q4** (confidentiality) | Production logs = ids/hashes/reason codes; egress = disclosure records listing REMOTE_SAFE fields only; **no remote LLM content persistence** |
| **Q5** | No auto-execute; assist ladder A3/A4; adversarial auto-approve cases FAIL closed ([SEC-03](./SEC-03-untrusted-content-adversarial-tests.md)) |
| **Q6** | Gate blocks PRIVATE_RAW; test capture grep finds no body bytes on wire; `RemoteSafeContext` only |
| **Q8** | FDE + vault encryption; gate answer cites threat tier: ciphertext only if machine locked |
| **Q9** | Cryptographic garbage; "stolen dir" test PASS; MK and OAuth absent from copied files |
| **Q10** | Untrusted input only; no credential exfil to LLM; no send/modify; injection cases in SEC-03 PASS; honest limit documented for logic bugs |

---

## 2. Minimisation PASS

**Question:** Did Enigma retain more than it needs?

**Fail modes:** Indefinite raw cache; attachments persisted by default; orphaned derivatives; sensitive inferences stored permanently; forget/decay not working; retained volume enables biography reconstruction despite encryption.

### Maps to

| Theme | Gate evidence |
| --- | --- |
| Retention TTLs | Per-class pilot table; GC tested (Q12) |
| Raw body cache limits | **7 day** pilot default; Gmail as archive of record (Q2) |
| No attachment persist default | Attachments do not persist unless explicit opt-in ([ADR-022](../../docs/adr/022-private-vault-storage.md)) |
| Derivative doesn't outlive justification | Full cascade on delete/expiry; lineage-driven forget (Q7, Q13) |
| Sensitive inferences not stored | Medical, sexuality, political, etc. — **NO** for pilot (Q14) |
| Forget / decay working | Inventory, provenance, scoped graph forget (Q15); DECAY ≠ FORGET |
| Red-line from retained **volume** | If sources lost, could Enigma alone reconstruct "quite a lot"? — minimisation lens on what exists (Q11 complements Reconstructability PASS) |

### Mapped questions

**Q2, Q4** (minimisation half: backup scope, log retention), **Q7, Q12, Q13, Q14, Q15**

### Dimension PASS criteria

- [ ] **Minimisation dimension PASS** — ALL mapped questions PASS with one-paragraph precise answers recorded
- [ ] ALL Minimisation-mapped checklist items below PASS with evidence links

| Question | PASS requires |
| --- | --- |
| **Q2** | Documented **7 day** pilot default (user-configurable); GC tested; Gmail documented as archive of record; not indefinite |
| **Q4** (minimisation) | Encrypted export only; backup scope documented; no wholesale vault sync to cloud; logs retain no raw body content |
| **Q7** | Blob deletion + SourceRecord cascade tested; **all derivative classes** cascade (embeddings, summaries, aggregates, inferred relations, cached chunks, source-derived features, audit material); no orphaned rows |
| **Q12** | Pilot TTL table implemented ([SEC-01](./SEC-01-secrets-encrypted-storage.md), [SEC-06](./SEC-06-retention-memory-decay-forget.md)); GC tests green; "store forever" not default |
| **Q13** | Full derivative cascade tested ([SEC-06](./SEC-06-retention-memory-decay-forget.md)); zero orphaned derived rows across all classes; lineage-driven forget |
| **Q14** | **Must be NO for pilot** — medical, sexuality, political, substance, intimate, financial distress, behavioural routines not persisted; test or write-path guard documented |
| **Q15** | Inventory ("what do you remember"), provenance ("why"), scoped forget as **graph operation** tested ([SEC-06](./SEC-06-retention-memory-decay-forget.md)) |

---

## 3. Reconstructability PASS

**Question:** Can the retained structure rebuild a biography?

**Fail modes:** Shadow DB reads like biography; global identity graph; prose summaries durable; reconstructability metrics > 0 on stripped benchmark; utility preserved only because shadow still contains narrative detail.

### Maps to

| Theme | Gate evidence |
| --- | --- |
| Shadow schema (enums not prose) | Opaque IDs, enums, coarse buckets — not reconstructive text ([ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md)) |
| Scoped aliases | Purpose-scoped graphs; no global narrative identity graph |
| SEC-07 benchmark | Dual metrics on stripped Alex DB (Q16) |
| Red-line reconstructability test | Four-layer lifecycle; Green/Amber/Red zones (Q11) |
| Lineage | `derived_from`, `purpose`, `retention_class` on derived rows |
| No global narrative graph | "Forget person" ≠ rename-to-`PERSON_Q7` and keep graph forever |

### Mapped questions

**Q11, Q16**

### Dimension PASS criteria

- [ ] **Reconstructability dimension PASS** — ALL mapped questions PASS with one-paragraph precise answers recorded
- [ ] ALL Reconstructability-mapped checklist items below PASS with evidence links

| Question | PASS requires |
| --- | --- |
| **Q11** | Documented answer is **not** "quite a lot"; four-layer lifecycle enforced; three zones (Green/Amber/Red); [data-retention.md](../../docs/architecture/data-retention.md) cited |
| **Q16** | **PASS** requires ([SEC-07](./SEC-07-shadow-reconstruction-benchmark.md)): reconstructability metrics **0**; utility metrics (attention, open-loop, dependency, next-action fidelity) **high**; target curve: biographical detail collapses much faster than executive-function usefulness. Cites [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md) |

---

## Lifecycle gate questions (Q1–Q16)

These sixteen questions must each be **PASS** with a one-paragraph precise answer recorded in the gate report. Each question belongs to one or more dimensions (see mapping above).

**Q11–Q16 (retention / reconstructability / shadow / forget):** implementation evidence from [SEC-06](./SEC-06-retention-memory-decay-forget.md) and [SEC-07](./SEC-07-shadow-reconstruction-benchmark.md); spec from [data-retention.md](../../docs/architecture/data-retention.md) and [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md).

| # | Question | Dimension(s) | PASS requires |
| --- | --- | --- | --- |
| **Q1** | Where is the raw email body stored? How is it encrypted? Where is the key? Who decrypts? | Confidentiality | `blobs/` + BLOB KEY wrapped by MK in Keychain; only Enigma Core ingest/retrieve paths decrypt; body never in `vault.db` inline |
| **Q2** | How long is raw body retained? | Minimisation | Documented **7 day** pilot default (user-configurable); GC tested; Gmail documented as archive of record; not indefinite |
| **Q3** | Do embeddings / FTS / vector indexes exist? Where stored? | Confidentiality | If yes: PRIVATE_DERIVED inside SQLCipher `vault.db` only; **no plaintext sidecar**; test proves no `vectors.db` under `private/` |
| **Q4** | What gets backed up? What gets logged? What leaves the computer? | Confidentiality · Minimisation | Encrypted export only; production logs = ids/hashes/reason codes; egress = disclosure records listing REMOTE_SAFE fields only; **no remote LLM content persistence**; backup scope minimised |
| **Q5** | Can email content cause a tool action without user approval? | Confidentiality | No auto-execute; assist ladder A3/A4; adversarial auto-approve cases FAIL closed ([SEC-03](./SEC-03-untrusted-content-adversarial-tests.md)) |
| **Q6** | Can Fireworks (or any remote provider) receive the raw email body? | Confidentiality | Gate blocks PRIVATE_RAW; test capture grep finds no body bytes on wire; `RemoteSafeContext` only |
| **Q7** | Can deleting a source remove all retained copies? | Minimisation | Blob deletion + SourceRecord cascade tested; **all derivative classes** cascade (embeddings, summaries, aggregates, inferred relations, cached chunks, source-derived features, audit material); no orphaned rows |
| **Q8** | Laptop stolen (disk locked) — what is exposed? | Confidentiality | FDE + vault encryption; gate answer cites threat tier: ciphertext only if machine locked |
| **Q9** | `~/.enigma/private/` copied without Keychain — what is exposed? | Confidentiality | Cryptographic garbage; "stolen dir" test PASS; MK and OAuth absent from copied files |
| **Q10** | Malicious email received — what can attacker achieve? | Confidentiality | Untrusted input only; no credential exfil to LLM; no send/modify; injection cases in SEC-03 PASS; honest limit documented for logic bugs |
| **Q11** | **Red-line reconstructability test:** If all original sources were lost tomorrow, how much of the user's life could be reconstructed from Enigma alone? | Reconstructability | Documented answer is **not** "quite a lot"; four-layer lifecycle enforced; three zones (Green/Amber/Red); [data-retention.md](../../docs/architecture/data-retention.md) cited |
| **Q12** | Is per-class retention policy documented and enforced? | Minimisation | Pilot TTL table implemented ([SEC-01](./SEC-01-secrets-encrypted-storage.md), [SEC-06](./SEC-06-retention-memory-decay-forget.md)); GC tests green; "store forever" not default |
| **Q13** | Is derived state deleted when source is deleted or expires? | Minimisation | Full derivative cascade tested ([SEC-06](./SEC-06-retention-memory-decay-forget.md)); zero orphaned derived rows across all classes; lineage-driven forget |
| **Q14** | Are sensitive inferences stored permanently? | Minimisation | **Must be NO for pilot** — medical, sexuality, political, substance, intimate, financial distress, behavioural routines not persisted; test or write-path guard documented |
| **Q15** | Are user forget operations planned and implemented? | Minimisation | Inventory ("what do you remember"), provenance ("why"), scoped forget as **graph operation** tested ([SEC-06](./SEC-06-retention-memory-decay-forget.md)) |
| **Q16** | **Shadow benchmark (dual metrics):** Populate Alex DB → strip keys, identity mapping, credentials, raw cache → score reconstructability ↓ and utility ↑ | Reconstructability | **PASS** requires ([SEC-07](./SEC-07-shadow-reconstruction-benchmark.md)): reconstructability metrics **0**; utility metrics (attention, open-loop, dependency, next-action fidelity) **high**; target curve: biographical detail collapses much faster than executive-function usefulness. Cites [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md) |

### Per-question sign-off

- [ ] **Q1** PASS — precise answer recorded
- [ ] **Q2** PASS — precise answer recorded
- [ ] **Q3** PASS — precise answer recorded
- [ ] **Q4** PASS — precise answer recorded (both Confidentiality and Minimisation halves)
- [ ] **Q5** PASS — precise answer recorded
- [ ] **Q6** PASS — precise answer recorded
- [ ] **Q7** PASS — precise answer recorded
- [ ] **Q8** PASS — precise answer recorded
- [ ] **Q9** PASS — precise answer recorded
- [ ] **Q10** PASS — precise answer recorded
- [ ] **Q11** PASS — precise answer recorded
- [ ] **Q12** PASS — precise answer recorded
- [ ] **Q13** PASS — precise answer recorded
- [ ] **Q14** PASS — precise answer recorded
- [ ] **Q15** PASS — precise answer recorded
- [ ] **Q16** PASS — precise answer recorded with SEC-07 dual-metric scores and target-curve assessment

### Dimension sign-off (gate unlock requires all three)

- [ ] **1. Confidentiality PASS** — Q1, Q3, Q4 (confidentiality half), Q5, Q6, Q8, Q9, Q10 + mapped checklist items
- [ ] **2. Minimisation PASS** — Q2, Q4 (minimisation half), Q7, Q12, Q13, Q14, Q15 + mapped checklist items
- [ ] **3. Reconstructability PASS** — Q11, Q16 + mapped checklist items

## PASS checklist

Each item must be **PASS** with evidence link (CI job, test name, or doc section). Items are grouped by primary dimension; cross-cutting items appear where they gate that dimension.

### Threat model & architecture (all dimensions)

- [ ] **SEC-00** threat model complete; network **and** storage lifecycle threats mapped
- [ ] [ADR-021](../../docs/adr/021-personal-data-security-boundary.md) accepted; [ADR-022](../../docs/adr/022-private-vault-storage.md) accepted; [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md) accepted; no contradictions with ADR-004/005/020

### Confidentiality — secrets & storage (SEC-01 / ADR-022)

- [ ] OAuth tokens in Keychain only — verified by test + manual grep checklist; **absent from vault.db**
- [ ] Dedicated GCP project documented; no shared personal project
- [ ] Vault layout: `vault.db` + `blobs/` + `audit/` + `config.json` under `~/.enigma/private/`
- [ ] SQLCipher (or equivalent) for `vault.db`; blob AEAD for `blobs/`
- [ ] MK wraps DATA / BLOB / AUDIT keys; stolen-dir test PASS
- [ ] SourceRecord + blob_ref pattern; no inline body duplication
- [ ] Derivative invariant: no plaintext vector/FTS sidecar
- [ ] `ENIGMA_HOME` not iCloud-synced; encrypted export-only backup documented
- [ ] Demo / Private / Shadow roots isolated ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md), [ADR-008](../../docs/adr/008-shadow-storage-roots.md))
- [ ] Safe logging: redaction tests green; dev raw-logging switch documented

### Confidentiality — egress gate (SEC-02)

- [ ] Single egress module; no stray provider clients in Private path
- [ ] `RemoteSafeContext` type enforced; PRIVATE_RAW / PRIVATE_DERIVED rejected at gate
- [ ] Allowlist + `may_send_remotely` enforced on all live inference paths
- [ ] **"What left my machine?"** disclosure API + UI functional
- [ ] ZDR documented as defence in depth only — gate passes without relying on vendor policy

### Confidentiality — adversarial / injection (SEC-03)

- [ ] All [`ADVERSARIAL_EMAIL_CASES`](../../packages/fixtures/src/personal_enigma/fixtures/adversarial_email_cases.py) PASS in CI
- [ ] Assist auto-approve injection cases FAIL closed (no execution)
- [ ] No credential-like strings in mock wire captures

### Minimisation — retention & existence (SEC-01 / SEC-06)

- [ ] Retention default **7 day** raw cache (pilot); resolved obligations 30–90 days; not "store forever"
- [ ] Per-class retention policy documented ([data-retention.md](../../docs/architecture/data-retention.md))
- [ ] Attachments **do not persist** by default (pilot)
- [ ] Embedding / index expiry **tied to source** — cascade on delete/expiry ([SEC-06](./SEC-06-retention-memory-decay-forget.md))
- [ ] **No permanent sensitive inference storage** (pilot Q14)
- [ ] Forget operations: inventory, provenance, scoped delete ([SEC-06](./SEC-06-retention-memory-decay-forget.md))
- [ ] Lineage fields on derived rows; forget-as-graph-operation tested ([SEC-06](./SEC-06-retention-memory-decay-forget.md))
- [ ] DECAY vs FORGET distinction tested — no alias-rename anti-pattern
- [ ] Derivative cascade exhaustive: embeddings, aggregates, inferred relations, cached chunks, source-derived features, audit material

### Reconstructability — shadow shape & benchmark (SEC-06 / SEC-07 / ADR-023)

- [ ] Pseudonymous shadow schema: enums/buckets over prose; reconstructability budget at write path ([ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md), [SEC-06](./SEC-06-retention-memory-decay-forget.md))
- [ ] No global narrative identity graph; scoped aliases only
- [ ] Shadow benchmark PASS with dual metrics ([SEC-07](./SEC-07-shadow-reconstruction-benchmark.md), Q16): reconstructability → 0; utility (attention, open-loop, dependency, next-action) → high; target curve documented

### Gmail connector (SEC-04) · LLM boundary (C09) · Operational (all dimensions)

- [ ] **`gmail.readonly` only** — scope enforcement test PASS
- [ ] No send/modify/trash API usage in codebase (grep gate)
- [ ] `ENIGMA_GMAIL_LIVE=1` (or equivalent) required for sync — default off
- [ ] Live sync writes SourceRecord + encrypted blob in Private vault only
- [ ] LLM has Enigma tools only — no Gmail credentials or provider superpowers
- [ ] No tool result → admits ignorance (Alex benchmark green)
- [ ] Remote inference disable-able end-to-end
- [ ] Operator runbook: connect, disconnect, rotate tokens, wipe Private mail cache, encrypted backup
- [ ] Incident note: what to do if disclosure log shows unexpected field
- [ ] Threat tier honest limits documented for unlocked-session / malware scenario

## Deliverables

- [ ] `personal_data_pilot_gate.py` (or equivalent) CLI that runs checklist + lifecycle questions and emits PASS/FAIL report **per dimension and overall**
- [ ] Gate report includes precise one-paragraph answers for Q1–Q16
- [ ] Gate report emits explicit **Confidentiality PASS / Minimisation PASS / Reconstructability PASS / GATE PASS** verdicts
- [ ] Checklist copied into this ticket stays in sync with runner
- [ ] Sign-off section in [personal-data-security.md](../../docs/architecture/personal-data-security.md) with date + git ref when PASS

## Acceptance criteria

- [ ] Runner exits non-zero on any FAIL (including any Q1–Q16 or any dimension FAIL)
- [ ] All checklist rows green in CI on main branch before Oscar inbox connect
- [ ] Explicit **human sign-off** field recorded (name + date) in gate report artifact
- [ ] No lifecycle question answered with "probably" or "TBD"
- [ ] Gate report demonstrates all three dimension PASSes independently — not only aggregate Q1–Q16 count

## Test plan

- Gate runner integration test with intentional FAIL injection per dimension (Confidentiality: Q6 raw-body wire; Minimisation: orphaned derivative; Reconstructability: injected name in shadow)
- Full CI pipeline includes adversarial + privacy + scope + stolen-dir tests

## Privacy constraints

Gate verification must not commit real mail bodies or tokens to artifacts.

**Unlocks:** Oscar's inbox (live Gmail on Private roots) — **only when Confidentiality PASS ∧ Minimisation PASS ∧ Reconstructability PASS**

## Related ADR

[ADR-021](../../docs/adr/021-personal-data-security-boundary.md) · [ADR-022](../../docs/adr/022-private-vault-storage.md) · [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md) · [data-retention.md](../../docs/architecture/data-retention.md)
