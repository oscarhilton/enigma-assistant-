# ADR-021: Personal Data Security Boundary — Untrusted LLM, Trusted Enigma Core

**Status:** Accepted  
**Date:** 2026-08-17

> **The LLM drives Enigma; security is why that split matters.**

## Context

Conversational UI ([ADR-020](./020-llm-conversational-boundary-not-truth.md)) established that the remote LLM is an **interpreter and planner**, not system authority. C09 landed tool-calling orchestration: the LLM selects Enigma capabilities; Enigma core holds truth, policy, memory, and execution.

Connecting a **real mailbox** (Oscar's inbox) crosses a new trust boundary. Email is **attacker-controlled input** — the OWASP LLM Top 10 class of **indirect prompt injection**. A malicious sender can craft subject lines, bodies, and HTML designed to manipulate the LLM into exfiltrating private context, approving harmful actions, or bypassing policy. Privacy invariants ([privacy-model.md](../architecture/privacy-model.md), [packages/privacy](../../packages/privacy)) already enforce select → transform → transmit last for **data minimisation**; for real personal data that pipeline is also a **security boundary**.

M11 landed read-only Gmail ingestion scaffolding (`gmail.py`, recorded HTTP fixtures). That code path is **not** sufficient to connect a live mailbox. v0-real personal-data pilot requires a dedicated security programme ([tickets/security/](../../tickets/security/)) before OAuth tokens touch production Private storage.

The reasoning value gate ([ADR-012](./012-reasoning-value-gate-decision.md)) demonstrated a related failure mode: privacy-safe structures passed `assert_remote_safe()` but never reached the model prompt — a **boundary violation at the wire**. Personal-data security generalises that lesson: every byte that leaves the machine must pass a **single audited egress gate**, not ad-hoc transport calls.

Provider zero-data-retention (ZDR) promises (e.g. Fireworks) are **insufficient** as the privacy boundary. Enigma must not transmit content merely because a vendor claims not to store it. The non-storing path is select → transform → gate → optional transmit — not "send because ZDR."

The network / LLM boundary is **only half** of a watertight personal-data pilot. The full **data lifecycle** — at-rest storage, key hierarchy, retention, derived indexes, logging, backups, and deletion — must be specified before connecting a live mailbox. **[SEC-01](../../tickets/security/SEC-01-secrets-encrypted-storage.md) (encryption) and [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md) (existence) are co-equal halves** of the storage plane: encryption protects what is retained; retention controls whether data should exist at all.

Design goal:

> **Compromise of any one ordinary boundary does not reveal the whole private world.**

This is not a claim of impossibility under active malware running as the user. Each layer defends a specific vector; no single ordinary failure (stolen locked laptop, copied `~/.enigma/private/`, leaked backup, compromised remote LLM) should expose wholesale private history. Full storage architecture: [ADR-022](./022-private-vault-storage.md).

Product claim:

> **Enigma deliberately forgets narrative detail while preserving enough state to remain useful.**

## Decision

### Trust boundary (canonical)

```text
Gmail → read-only ingestion → raw private records → normalise / classify / retrieve
                                                              ↓
                                                    privacy transform
                                                              ↓
                                                    REMOTE-SAFE CONTEXT
                                                              ↓
                                                    UNTRUSTED LLM (interpreter / planner)
                                                              ↓
                                                    typed tool request
                                                              ↓
                                            ┌─────────────────────────┐
                                            │   SECURITY BOUNDARY     │
                                            └─────────────────────────┘
                                                              ↓
                                                    deterministic policy → Enigma Core
```

### Role split (extends ADR-020)

| Component | Holds | Must never |
| --- | --- | --- |
| **Untrusted LLM** | User message + remote-safe tool schemas + structured tool results | Gmail credentials; `gmail.search()` / `gmail.send()` superpowers; raw mail bodies; authority over policy outcomes |
| **Enigma Core** | Raw private records, OAuth tokens, policy, execution | Delegate credential access or unconstrained side effects to the LLM |

The LLM receives **Enigma capabilities** (typed tools backed by deterministic handlers), not provider APIs.

### Security invariants

1. **Select → transform → transmit last** is a **security invariant**, not only privacy etiquette. Untransformed private records never cross the egress gate.
2. **Raw email is local-only.** Full MIME bodies, headers with PII, and attachment bytes stay in encrypted Private storage; remote paths receive only transformed, allowlisted structures ([packages/privacy allowlist](../../packages/privacy/README.md)).
3. **Email is hostile input.** Ingestion, retrieval, and conversational tools must treat message content as untrusted evidence — never as instructions to the LLM or Enigma policy layer.
4. **v0-real scope: `gmail.readonly` only.** Nothing in the pilot may alter the mailbox (send, modify labels, delete, draft). Separate OAuth scopes for readonly / send / modify are **future capabilities**, each with its own ticket and authority rung ([ADR-019](./019-delegated-authority-and-execution-ladder.md)).
5. **No autonomous consequential actions.** Assist propose → explicit approval → verified result ([ADR-020](./020-llm-conversational-boundary-not-truth.md), [C07](../../tickets/conversational-ui/C07-assist-proposals.md)). Real-mail pilot adds no auto-send, auto-reply, or auto-delete.
6. **Single audited egress gateway.** All remote inference (Fireworks, OpenAI, future providers) flows through one module that enforces allowlist, `may_send_remotely`, transformation, logging, and per-request disclosure records.
7. **Data lifecycle is co-equal with the network boundary.** Raw bodies, derived indexes, OAuth tokens, and audit records each have defined storage, encryption, retention, and deletion semantics ([ADR-022](./022-private-vault-storage.md)). **[SEC-01](../../tickets/security/SEC-01-secrets-encrypted-storage.md) (encryption) and [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md) (existence) are co-equal halves** — encryption protects what is retained; retention controls whether data should exist at all.
8. **Four-layer data lifecycle (canonical).** SOURCE WORLD → ACTIVE PRIVATE STATE → PSEUDONYMOUS SHADOW → FORGET ([data-retention.md](../architecture/data-retention.md), [ADR-023](./023-persistent-shadow-abstract-state-not-biography.md)). Each layer has distinct retention rules; FORGET is a terminal state, not merely TTL expiry.
9. **No retained derivative may outlive its justification merely because it is derived.** Applies to embeddings, interaction-frequency aggregates, inferred relations, cached retrieval chunks, source-derived features, and historical audit material. **"Delete raw data" alone is NOT successful forgetting** ([SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md)).
10. **Retention minimises reconstructability, not just storage size.** Risk ≈ sensitivity × breadth × time depth × cross-linkability × identifiability × accessibility. **Red-line test:** if Enigma lost all original sources tomorrow, could someone reconstruct "quite a lot" of the user's life from Enigma alone? If yes → too far. Enigma is working memory, not a second permanent archive ([data-retention.md](../architecture/data-retention.md)). **Pseudonymous shadow:** durable state is abstract (opaque IDs, enums, scoped graphs) — not biography ([ADR-023](./023-persistent-shadow-abstract-state-not-biography.md)).
11. **DECAY ≠ FORGET.** DECAY reduces detail, precision, and linkability while retaining utility. FORGET drives recoverability to zero within Enigma. "Forget this person" must **not** mean "replace name with `PERSON_Q7` and keep everything forever."
12. **Sensitive inferences are a special class.** No permanent pilot storage of medical, sexuality, political, substance, intimate, financial-distress, or behavioural-routine inferences. Deletion cascades to derived state — not just raw blobs.
13. **Shadow benchmark (dual metrics) before Gmail pilot.** Scored benchmark ([SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md), [SEC-05 Q16](../../tickets/security/SEC-05-personal-data-pilot-gate.md)): privacy ↓ reconstructability metrics → **0**; utility ↑ (attention, open-loop, dependency, next-action fidelity) → **high**. Target curve — **the real Enigma bet:** biographical detail collapses much faster than executive-function usefulness.

### Data lifecycle & storage

Personal-data security requires **typed data classification** and **encrypted vault storage** before Gmail lands. Summary; full specification in [ADR-022](./022-private-vault-storage.md).

#### Classification model

| Class | Examples | May cross egress gate |
| --- | --- | --- |
| **SECRET** | OAuth refresh, encryption keys, device keys | Never |
| **PRIVATE_RAW** | Email bodies, attachments, note bodies | Never |
| **PRIVATE_DERIVED** | Obligations, people graph, summaries, embeddings, FTS, vector index | Never (transform → REMOTE_SAFE first) |
| **REMOTE_SAFE** | Pseudonymous transformed context | Yes — sole egress payload class |
| **PUBLIC** | Non-personal config, schemas | Yes |

Future code paths enforce typed boundaries: `PrivateRaw[T]`, `PrivateDerived[T]`, `RemoteSafe[T]`. Remote / LLM paths accept only `RemoteSafeContext`.

#### Key hierarchy (summary)

```text
OS Keychain: OAuth refresh · Master key · Device identity
Master key wraps → DATA KEY (vault.db) · BLOB KEY (blobs/) · AUDIT KEY (audit/)
```

Stealing `~/.enigma/private/` alone → cryptographic garbage. OAuth refresh tokens are **Keychain-only** — never in `vault.db` — separating historical data theft from ongoing Gmail access.

#### Retention & reconstructability (summary)

Full model: [data-retention.md](../architecture/data-retention.md) · [ADR-022 retention section](./022-private-vault-storage.md#retention--reconstructability-boundary).

- **Red-line test** and **three zones** (Green / Amber / Red) govern what may persist.
- Pilot defaults (aggressive; user-configurable): raw email bodies **7 day** cache max; attachments **do not persist** by default; resolved obligations **30–90 days** then discard/compress; embeddings **expire with source**; remote LLM payloads **no content persistence** (hash/audit only).
- **"Store everything forever" is not the default.** The safest Enigma knows what is worth forgetting.

#### Derivative invariants

> **No private derivative may be persisted outside the encrypted vault.**

Embeddings, vector indexes, FTS, summaries, and semantic labels are **PRIVATE_DERIVED** inside SQLCipher-protected `vault.db`. Forbidden: encrypted `vault.db` + plaintext `vectors.db`.

> **No retained derivative may outlive its justification merely because it is derived.**

Derivatives carry lightweight **lineage** ([data-retention.md](../architecture/data-retention.md#lineage-schema)): `derived_from`, `purpose`, `retention_class`, `expires_after_resolution`. Enables deterministic `forget(SRC_123)` as a **graph operation** — not best-effort DB delete.

#### SourceRecord pattern

Structured rows (`SourceRecord`: id, source, external_id, received_at, content_hash, blob_ref) reference encrypted blobs — raw body is **not** duplicated across Obligation/Evidence tables. Deletion removes blob + references sanely.

Cross-links: [ADR-004](./004-notes-best-effort-no-sqlite.md) (Notes HIGH, no SQLite scraping), [ADR-005](./005-demo-private-storage-roots.md) (Demo/Private/Shadow root separation).

### Six requirements before connecting a live mailbox

| # | Requirement | Ticket |
| --- | --- | --- |
| 1 | Threat model documented; email-as-attacker-input explicit | [SEC-00](../../tickets/security/SEC-00-personal-data-threat-model.md) |
| 2 | Read-only OAuth + dedicated Google Cloud project + Keychain token storage | [SEC-01](../../tickets/security/SEC-01-secrets-encrypted-storage.md) |
| 3 | Private vault: encrypted SQLite + blob store + key hierarchy + retention ([ADR-022](./022-private-vault-storage.md), [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md)) | [SEC-01](../../tickets/security/SEC-01-secrets-encrypted-storage.md) |
| 4 | Single audited remote egress gate + "What left my machine?" disclosure | [SEC-02](../../tickets/security/SEC-02-audited-remote-egress-gate.md) |
| 5 | Adversarial email corpus + prompt-injection tests in Alex demo | [SEC-03](../../tickets/security/SEC-03-untrusted-content-adversarial-tests.md) |
| 6 | Gmail read-only connector (`gmail.readonly` only) wired to Private roots | [SEC-04](../../tickets/security/SEC-04-gmail-readonly-connector.md) |

All six must **PASS** the hard checklist in [SEC-05](../../tickets/security/SEC-05-personal-data-pilot-gate.md) before Oscar's inbox is connected.

### Three gate dimensions (SEC-05)

Before Oscar's inbox connects, [SEC-05](../../tickets/security/SEC-05-personal-data-pilot-gate.md) requires **three separate dimension PASSes** — not a composite score. Each dimension PASSes only if **every** mapped question and checklist item for that dimension PASSes. **Any dimension FAIL → gate FAIL**, even if the other two PASS.

> **Database encrypted ≠ safe.** SQLCipher and blob AEAD satisfy Confidentiality (ciphertext at rest). They do **not** satisfy Minimisation (did we retain more than we need?) or Reconstructability (does retained structure still rebuild a biography?). A fully encrypted vault with indefinite raw cache, orphaned derivatives, and biography-shaped shadow rows is a gate FAIL.

| # | Dimension PASS | Core question | Questions |
| --- | --- | --- | --- |
| 1 | **Confidentiality** | Can retained data be read if storage is stolen? | Q1, Q3, Q4 (wire/backup/log), Q5, Q6, Q8, Q9, Q10 |
| 2 | **Minimisation** | Did Enigma retain more than it needs? | Q2, Q4 (backup/log retention), Q7, Q12, Q13, Q14, Q15 |
| 3 | **Reconstructability** | Can the retained structure rebuild a biography? | Q11, Q16 |

**Confidentiality** maps to encryption, Keychain separation, stolen-dir test, egress without raw leak, adversarial injection containment. **Minimisation** maps to retention TTLs, raw body cache limits, no attachment persist default, derivative cascade, sensitive inference non-storage, forget/decay. **Reconstructability** maps to shadow schema (enums not prose), scoped aliases, lineage, no global narrative graph, and [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) dual metrics (Q16).

Canonical dimension sections, PASS criteria, and checklist mapping: [SEC-05 gate verdict](../../tickets/security/SEC-05-personal-data-pilot-gate.md#gate-verdict--three-separate-passes).

### "What left my machine?" disclosure

Every remote inference request must produce a **falsifiable, user-inspectable record** of what crossed the egress gate: payload hash, allowlist field summary, transformation profile, provider, timestamp, and correlation id. This is the product-facing privacy/security boundary — not vendor ZDR marketing.

Implementation lands in [SEC-02](../../tickets/security/SEC-02-audited-remote-egress-gate.md) (gate + ledger) with UI surfacing as acceptance criteria there.

### Adversarial corpus before real mail

Malicious-email injection cases run against the **Alex demo** simulation path ([SEC-03](../../tickets/security/SEC-03-untrusted-content-adversarial-tests.md)) before SEC-04 connects OAuth to Private storage. Seed case manifest: [`adversarial_email_cases.py`](../../packages/fixtures/src/personal_enigma/fixtures/adversarial_email_cases.py).

### Programme sequence

```text
C09 (LLM tool boundary, done)
  → SEC-00 (threat model)
  → SEC-01 (secrets + encrypted storage)
  → SEC-02 (audited egress gate)
  → SEC-03 (adversarial tests)
  → SEC-04 (Gmail read-only connector)
  → SEC-06 (retention + memory decay + forget — co-equal half of SEC-01)
  → SEC-07 (shadow benchmark — dual metrics)
  → SEC-05 (hard PASS pilot gate — three dimensions)
  → Oscar's inbox
```

SEC-05 is a **hard PASS checklist gate**, not a vibes review. Any FAIL blocks live mailbox connection. Unlock requires **Confidentiality PASS ∧ Minimisation PASS ∧ Reconstructability PASS** ([SEC-05](../../tickets/security/SEC-05-personal-data-pilot-gate.md#gate-verdict--three-separate-passes)).

### Fireworks / provider ZDR

Zero-data-retention and similar provider policies are **defence in depth**, not the Enigma boundary. Code must assume:

- Misconfiguration could send disallowed fields until the egress gate rejects them.
- Provider promises do not replace local transformation, allowlisting, and disclosure logging.
- Remote inference remains disable-able; ingestion and local transform must work with `RemoteInferenceConfig(enabled=False)`.

## Consequences

- Real Gmail connection is **blocked** until SEC-05 PASS. M11 scaffold remains fixture/CI-only for Private pilot.
- C05e / C08 live paths must route through SEC-02 egress gate when touching Private data.
- New OAuth scopes (send, modify) require separate ADR amendments and SEC follow-on tickets — not scope creep in SEC-04.
- Agents must not wire `OPENAI_API_KEY` / Fireworks transport directly from handlers; all remote calls go through the audited gate.
- Demo Mode continues to use isolated storage roots ([ADR-005](./005-demo-private-storage-roots.md)); adversarial tests run on Alex demo, not Oscar's mailbox.
- Private vault layout, classification types, and derivative invariant are architectural prerequisites documented in [ADR-022](./022-private-vault-storage.md); SEC-05 gate requires precise PASS/FAIL answers for each lifecycle question.

## Related

- [ADR-022 — Private vault storage](./022-private-vault-storage.md)
- [ADR-023 — Persistent shadow](./023-persistent-shadow-abstract-state-not-biography.md)
- [ADR-004 — Notes best-effort; no SQLite scraping](./004-notes-best-effort-no-sqlite.md)
- [ADR-005 — Demo vs Private storage roots](./005-demo-private-storage-roots.md)
- [ADR-020 — LLM conversational boundary](./020-llm-conversational-boundary-not-truth.md)
- [ADR-012 — Reasoning value gate](./012-reasoning-value-gate-decision.md)
- [ADR-019 — Delegated authority ladder](./019-delegated-authority-and-execution-ladder.md)
- [personal-data-security.md](../architecture/personal-data-security.md)
- [ADR-023 — Persistent shadow](./023-persistent-shadow-abstract-state-not-biography.md)
- [data-retention.md](../architecture/data-retention.md)
- [privacy-model.md](../architecture/privacy-model.md)
- [tickets/security/](../../tickets/security/) · [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md) · [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md)
