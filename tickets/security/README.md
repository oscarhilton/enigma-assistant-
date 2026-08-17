# Personal data security programme (SEC-00–SEC-07)

**Status:** SEC-00–SEC-03 done — **SEC-04 in-progress** (fixture pipeline green; live TEST mailbox smoke pending) — **SEC-06 done** — SEC-05/SEC-07 pending  
**North star:** Real personal data only after falsifiable security boundaries; email is hostile input.

> Documentation phase frozen 2026-08-17. No security-architecture gardening unless implementation contradiction. Implementation order: SEC-00 → SEC-01 → SEC-02 → SEC-03 → SEC-04 → SEC-06 → SEC-07 → SEC-05 gate.

## Three PASSes before Oscar's inbox

[SEC-05](./SEC-05-personal-data-pilot-gate.md) requires **three separate dimension PASSes** — not a composite score. **Any dimension FAIL → gate FAIL**, even if the other two PASS.

| # | Dimension PASS | Core question |
| --- | --- | --- |
| **1** | **Confidentiality PASS** | Can retained data be read if storage is stolen? |
| **2** | **Minimisation PASS** | Did Enigma retain more than it needs? |
| **3** | **Reconstructability PASS** | Can the retained structure rebuild a biography? |

Each dimension PASSes only if **every** mapped Q1–Q16 question and checklist item for that dimension PASSes.

> **Database encrypted ≠ safe.** Encryption satisfies Confidentiality; it does not satisfy Minimisation or Reconstructability. A fully encrypted vault that retains too much, for too long, in biography-shaped structure is still a gate FAIL.

> **Ethics creed before real inbox:** Know only what is necessary · Infer only for a purpose · Remember less than you could · Make memory and action inspectable · the user is the subject of Enigma, never its raw material ([ethics.md](../../docs/architecture/ethics.md) · [ADR-026](../../docs/adr/026-ethics-creed-user-is-subject.md)).

> **Prerequisite for Oscar's inbox:** C09 done → SEC-00 … SEC-07 → SEC-05 **Confidentiality ∧ Minimisation ∧ Reconstructability PASS** → live Gmail OAuth on Private roots.

> **SEC-04 success criterion:** synthetic **nasty test mailbox** on a Google TEST account survives the full private pipeline — **not** Oscar's inbox. Manifest: [`nasty_mailbox_manifest.py`](../../packages/fixtures/src/personal_enigma/fixtures/nasty_mailbox_manifest.py).

> **C10 deferred:** [Cortex brain visualizer](../conversational-ui/C10-cortex-brain-visualizer.md) remains off the critical path until SEC-04 pipeline + SEC-02 audit semantics stabilise.

> **The real Enigma bet:** biographical detail collapses much faster than executive-function usefulness ([SEC-07](./SEC-07-shadow-reconstruction-benchmark.md) dual metrics, Q16).

## Two co-equal security planes

Personal-data security is **not** only the network / LLM boundary. The **storage / data lifecycle** is equally gate-critical before claiming watertight:

| Plane | What it covers | Primary docs |
| --- | --- | --- |
| **Network / LLM boundary** | Remote inference egress, transform, allowlist | [ADR-021](../../docs/adr/021-personal-data-security-boundary.md), SEC-02, SEC-03 |
| **Storage / data lifecycle** | Vault layout, keys, retention, derivatives, logging, backups, deletion, forget | [ADR-022](../../docs/adr/022-private-vault-storage.md), [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md), [data-retention.md](../../docs/architecture/data-retention.md), SEC-01, SEC-06, SEC-07, SEC-05 |

Within the storage plane, **SEC-01 (encryption) and SEC-06 (existence) are co-equal halves** — encryption protects what is retained; retention controls whether data should exist at all.

Design goal ([ADR-021](../../docs/adr/021-personal-data-security-boundary.md)):

> **Compromise of any one ordinary boundary does not reveal the whole private world.**

## Four-layer data lifecycle

```text
SOURCE WORLD          raw · identifiable · short-lived (PRIVATE_RAW blobs)
       ↓ extract
ACTIVE PRIVATE STATE  purpose-bound — only what Enigma currently needs
       ↓ decay — detail↓ precision↓ linkability↓ utility retained
PSEUDONYMOUS SHADOW   enums · buckets · state transitions · low narrative reconstructability
       ↓ expiry — recoverability → zero
FORGET
```

**DECAY ≠ FORGET:** DECAY compresses while retaining utility. FORGET is terminal. "Forget this person" must **not** mean rename-to-`PERSON_Q7` and keep the graph forever.

Full spec: [data-retention.md](../../docs/architecture/data-retention.md) · [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md)

## Prominent invariant

> **No retained derivative may outlive its justification merely because it is derived.**

Applies to embeddings, interaction-frequency aggregates, inferred relations, cached retrieval chunks, source-derived features, historical audit material. **"Delete raw data" alone is NOT successful forgetting.**

Derivatives carry **lineage** (`derived_from`, `purpose`, `retention_class`, `expires_after_resolution`) so `forget(source_id)` is a **graph operation**.

## Three gate dimensions (SEC-05 detail)

Full dimension sections, PASS criteria, and checklist mapping: [SEC-05](./SEC-05-personal-data-pilot-gate.md#gate-verdict--three-separate-passes).

| Dimension | Core question | Questions |
| --- | --- | --- |
| **Confidentiality** | Can retained data be read if storage is stolen? | Q1, Q3, Q4 (wire/backup/log), Q5, Q6, Q8, Q9, Q10 |
| **Minimisation** | Did Enigma retain more than it needs? | Q2, Q4 (backup/log retention), Q7, Q12, Q13, Q14, Q15 |
| **Reconstructability** | Can the retained structure rebuild a biography? | Q11, Q16 |

Q16 uses [SEC-07](./SEC-07-shadow-reconstruction-benchmark.md) **dual metrics**: privacy ↓ reconstructability → 0 **and** utility ↑ (attention, open-loop, dependency, next-action fidelity) → high. Target curve: biographical detail collapses much faster than executive-function usefulness.

## Architectural rules (from ADR-021 + ADR-022 + ADR-023)

1. **LLM drives Enigma; LLM is not Enigma** — extends [ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md).
2. **Select → transform → transmit last** is a **security invariant**, not only privacy.
3. **Data lifecycle is co-equal with network boundary** — storage, keys, retention, derivatives, logging, backups ([ADR-022](../../docs/adr/022-private-vault-storage.md), [data-retention.md](../../docs/architecture/data-retention.md)).
4. **SEC-01 + SEC-06 are co-equal storage halves** — encryption + existence.
5. **Four-layer lifecycle** — SOURCE WORLD → ACTIVE PRIVATE STATE → PSEUDONYMOUS SHADOW → FORGET.
6. **Typed classification** — SECRET · PRIVATE_RAW · PRIVATE_DERIVED · REMOTE_SAFE · PUBLIC; egress accepts REMOTE_SAFE only.
7. **Raw email stays local** — encrypted blobs + SourceRecord; remote paths receive transformed context only.
8. **Derivative invariants** — no embeddings / FTS / vectors outside encrypted vault; no derivative outlives its justification.
9. **Email is attacker-controlled input** — indirect prompt injection (OWASP LLM Top 10).
10. **v0-real: `gmail.readonly` only** — send/modify are separate future capabilities/scopes.
11. **Single audited egress gate** — no ad-hoc Fireworks/OpenAI calls from handlers.
12. **Provider ZDR ≠ Enigma boundary** — do not transmit because vendor promises not to store.
13. **SEC-05 is a hard PASS gate** — sixteen precise lifecycle questions (Q1–Q16) across three dimensions; not a vibes review.
14. **Retention minimises reconstructability** — red-line test; Green/Amber/Red zones; aggressive pilot TTLs; embeddings expire with source.
15. **Sensitive inferences are a special class** — no permanent pilot storage; deletion cascades to derived state.
16. **The safest Enigma knows what to forget** — DECAY vs FORGET; lineage; graph forget ([SEC-06](./SEC-06-retention-memory-decay-forget.md)).

## Trust boundary

```text
Gmail (gmail.readonly — TEST account nasty mailbox)
  → ingestion (hostile MIME) → SourceRecord + encrypted blob (PRIVATE_RAW — SOURCE WORLD)
                              ↓
                    vault.db (PRIVATE_DERIVED — ACTIVE STATE → PSEUDONYMOUS SHADOW)
                              ↓
                         transform → REMOTE-SAFE CONTEXT
                                              ↓
                                    UNTRUSTED LLM
                                              ↓
                                    typed tool request
                                              ↓
                                [ security boundary — RemoteSafeContext only ]
                                              ↓
                                    Enigma Core (policy · execution)

Keychain: OAuth refresh · Master key · Device identity  (never in vault.db)
```

**SEC-04 legacy guard:** when `persistence_backend == legacy_plaintext`, Gmail ingestion is **refused** — no fallback or dev exception during evaluation.

## Tickets

| Ticket | Title | Status |
| --- | --- | --- |
| [SEC-00](./SEC-00-personal-data-threat-model.md) | Personal-data threat model (network + storage) | done |
| [SEC-01](./SEC-01-secrets-encrypted-storage.md) | Secrets + Private vault (ADR-022) — encryption half | done |
| [SEC-02](./SEC-02-audited-remote-egress-gate.md) | Single audited remote egress gate | done |
| [SEC-03](./SEC-03-untrusted-content-adversarial-tests.md) | Untrusted-content / prompt-injection tests | done |
| [SEC-04](./SEC-04-gmail-readonly-connector.md) | Real external source through private architecture (nasty TEST mailbox) | **in-progress** |
| [SEC-05](./SEC-05-personal-data-pilot-gate.md) | Personal-data pilot gate (hard PASS + Q1–Q16, three dimensions) | todo |
| [SEC-06](./SEC-06-retention-memory-decay-forget.md) | Retention + memory decay + forget — existence half | **done** |
| [SEC-07](./SEC-07-shadow-reconstruction-benchmark.md) | Shadow benchmark — dual metrics (reconstructability ↓ utility ↑) | todo |

## Claim order

1. **SEC-00** — threat model + architecture doc (documentation; can parallel SEC-01 design)
2. **SEC-01** — Keychain tokens, Private vault layout, SourceRecord + blobs, encryption, derivative vault invariant
3. **SEC-02** — egress gate + `RemoteSafeContext` + "What left my machine?" disclosure (hard-depends SEC-01 for encrypted `audit/`)
4. **SEC-03** — adversarial corpus in Alex demo (hard-depends C09; soft-depends SEC-02 for egress assertions)
5. **SEC-04** — prove real external source (`gmail.readonly` + nasty TEST mailbox) through encrypted vault pipeline; `persistence_backend == legacy_plaintext` → refuse (hard-depends SEC-01, SEC-02, SEC-03)
6. **SEC-06** — retention policy, four-layer decay, lineage, graph forget (hard-depends SEC-01; co-equal half)
7. **SEC-07** — shadow benchmark dual metrics (hard-depends SEC-06)
8. **SEC-05** — checklist gate + sixteen lifecycle questions across three dimensions (hard-depends SEC-00–SEC-04, SEC-06, SEC-07)

Do **not** connect Oscar's inbox or point Private OAuth at production mail until SEC-05 PASS (including Q1–Q16 and all three gate dimensions).

## Docs

- [docs/adr/021-personal-data-security-boundary.md](../../docs/adr/021-personal-data-security-boundary.md) — network / LLM boundary + three gate dimensions
- [docs/adr/022-private-vault-storage.md](../../docs/adr/022-private-vault-storage.md) — vault layout, classification, lifecycle
- [docs/adr/023-persistent-shadow-abstract-state-not-biography.md](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md) — pseudonymous shadow shape, lineage, dual metrics
- [docs/architecture/personal-data-security.md](../../docs/architecture/personal-data-security.md) — programme overview
- [docs/architecture/data-retention.md](../../docs/architecture/data-retention.md) — four layers, lineage schema, derivative invariant, DECAY vs FORGET
- [docs/architecture/ethics.md](../../docs/architecture/ethics.md) · [ADR-026](../../docs/adr/026-ethics-creed-user-is-subject.md) — ethics creed before real inbox; detective-show trap is a SEC-07 FAIL
- [docs/architecture/privacy-model.md](../../docs/architecture/privacy-model.md)
- [ADR-004](../../docs/adr/004-notes-best-effort-no-sqlite.md) · [ADR-005](../../docs/adr/005-demo-private-storage-roots.md) — Notes privacy + Demo/Private separation
- Conversational UI prerequisite: [C09](../conversational-ui/C09-llm-conversational-boundary.md)
- Shareable recipes ([ADR-024](../../docs/adr/024-shareable-recipes-procedure-never-personal-state.md) · [REC00](../recipes/REC00-shareable-recipes-north-star.md) `future`) wait on C09 LLM proof **and** this programme's SEC-05 PASS — not a SEC implementation ticket

## Branch naming

`ticket/SEC00-slug` … `ticket/SEC07-slug` (distinct from Shadow `SE*` tickets).
