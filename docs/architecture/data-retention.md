# Data retention & reconstructability boundary

**Status:** Architecture programme (ADR-021, ADR-022, ADR-023) — implementation not started  
**Date:** 2026-08-17  
**Related:** [personal-data-security.md](./personal-data-security.md) · [ethics.md](./ethics.md) · [ADR-026](../adr/026-ethics-creed-user-is-subject.md) · [cortex-visualizer.md](./cortex-visualizer.md) · [ADR-021](../adr/021-personal-data-security-boundary.md) · [ADR-022](../adr/022-private-vault-storage.md) · [ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md) · [ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [ADR-029](../adr/029-context-compilation-request-shaped-memory.md) · [tone-memory.md](./tone-memory.md) · [SEC-01](../../tickets/security/SEC-01-secrets-encrypted-storage.md) · [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md) · [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) · [SEC-05 Q11–Q16](../../tickets/security/SEC-05-personal-data-pilot-gate.md#lifecycle-gate-questions-pass--fail)

## Thesis

> **The safest Enigma isn't the one that can remember everything. It's the one that knows what is worth forgetting.**

> **Enigma deliberately forgets narrative detail while preserving enough state to remain useful.**

Risk is **not** measured in megabytes stored. Risk is approximate:

```text
risk ≈ sensitivity × breadth × time depth × cross-linkability × identifiability × accessibility
```

Enigma is **working memory**, not a second permanent archive of the user's life. Enigma stores an **index of what matters**, not **your life** ([ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md)). Design principle:

> **Retain minimum sufficient state, not maximum available history.**

Ethics form: **minimum state for the current purpose, not "how complete a model of this human."** Curiosity is not a retention justification — the detective-show trap ([ethics.md](./ethics.md) · [SEC-07 detective framing](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md#detective-show-trap) · [ADR-026](../adr/026-ethics-creed-user-is-subject.md)).

**SEC-01 (encryption) and SEC-06 (existence) are co-equal halves** of the storage plane: encryption protects what is retained; retention controls whether data should exist at all.

## Prominent invariant

> **No retained derivative may outlive its justification merely because it is derived.**

Applies to:

- Embeddings, vector indexes, FTS tables
- Interaction-frequency aggregates
- Inferred relations and semantic labels
- Cached retrieval chunks
- Source-derived features
- Historical audit material tied to forgotten scope

**"Delete raw data" alone is NOT successful forgetting.** Derivatives must carry lineage and participate in deterministic forget cascades.

## Four-layer lifecycle (canonical)

Retention governs **how long** data survives; [ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md) governs **what shape** durable memory takes. Evidence flows through four layers:

```text
SOURCE WORLD          raw · identifiable · short-lived
  email / calendar / messages / notes
        │
        │ extract
        ▼
ACTIVE PRIVATE STATE  purpose-bound — only what Enigma currently needs
  obligations · blockers · availability · evidence refs · typed transitions
        │
        │ decay — detail↓ precision↓ linkability↓ utility retained
        ▼
PSEUDONYMOUS SHADOW   enums · buckets · state transitions · low narrative reconstructability
  durable working memory — PRIVATE_DERIVED in encrypted vault.db
        │
        │ expiry — recoverability → zero within Enigma
        ▼
FORGET
```

| Layer | Stance | Classification | Default lifetime |
| --- | --- | --- | --- |
| **Source world** | Transient cache; Gmail/calendar are archive of record | PRIVATE_RAW blobs | Short (7 day pilot default) |
| **Active private state** | Purpose-bound facts while obligation / attention active | PRIVATE_DERIVED (active) | While relevant → decay |
| **Pseudonymous shadow** | Abstract state machine — not biography | PRIVATE_DERIVED (durable shape) | Until justification expires |
| **Forget** | Recoverability → zero | Deleted | Terminal |

### DECAY vs FORGET (hard distinction)

| | DECAY | FORGET |
| --- | --- | --- |
| **Effect** | detail↓ precision↓ linkability↓ | recoverability → **zero** within Enigma |
| **Utility** | Retained — Enigma stays useful | N/A — data gone |
| **Example** | Prose → `due_bucket=WITHIN_3_DAYS` enum | Remove all rows derived exclusively from `SRC_123` |

**Anti-pattern:** "Forget this person" → rename to `PERSON_Q7` and keep the full correspondence graph forever. That is pseudonymisation, not forgetting.

Memory decay ([SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md)) applies across **source world** and **active private state** — progressive abstraction into shadow form, then FORGET when justification expires.

**Good vs bad shadow (examples):**

```text
BAD:  "Joe Atkinson annoyed with Oscar about Believ charger rollout..."
GOOD: OBLIGATION_81 · actor=SELF · related_entity=PROJECT_R9 · due_bucket=WITHIN_3_DAYS · source_evidence=SOURCE_9182
```

## Lineage schema

Shadow and active-state records carry lightweight lineage enabling deterministic forget as a **graph operation**:

```yaml
derived_from: [SRC_123, SRC_188]
purpose: OPEN_LOOP_TRACKING
retention_class: ACTIVE_UNTIL_RESOLVED
expires_after_resolution: 30d
```

| Field | Purpose |
| --- | --- |
| `derived_from` | Source ids this record depends on |
| `purpose` | Why Enigma retained this (e.g. `OPEN_LOOP_TRACKING`, `ATTENTION_RANKING`) |
| `retention_class` | When justification ends (e.g. `ACTIVE_UNTIL_RESOLVED`, `EPHEMERAL_ANSWER_ONLY`) |
| `expires_after_resolution` | Post-resolution TTL before shadow → FORGET |

`forget(SRC_123)` answers:

1. What depends **exclusively** on this source?
2. What has **independent evidence**?
3. What **must disappear**?
4. What can **remain but lose confidence**?

"Forget everything about X" = graph operation, not best-effort DB delete.

## Red-line test

Before retaining any data class, ask:

> **If Enigma lost access to all original sources tomorrow, how much of my life could someone reconstruct from Enigma alone?**

If the honest answer is **"quite a lot"** → retention has gone too far. The vault must not become a shadow copy of the person.

This test applies to **derived state** as well as raw blobs. Embeddings, inferred preferences, and cross-linked graphs can reconstruct more than the original source fragments — deletion must cascade to derived material, not just raw bodies.

### Shadow benchmark — dual metrics

Operational form of the red-line test — required before Gmail pilot ([SEC-05 Q16](../../tickets/security/SEC-05-personal-data-pilot-gate.md), [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md)):

1. Populate fixture DB (Alex) through ingest + decay.
2. Strip keys, identity mappings, credentials, PRIVATE_RAW cache.
3. Hand remainder to motivated analyst / model.
4. Score reconstructability ↓ and utility ↑ independently.

**Research question:** *How much biography can we destroy before Enigma stops being useful?*

**Target curve:** personal reconstructability collapses **faster** than executive-function usefulness.

| Reconstructability (→ **0**) | Utility (→ **high**) |
| --- | --- |
| Real names recovered | Attention fidelity |
| Specific message content | Open-loop fidelity |
| Employers / named projects | Dependency fidelity |
| Precise locations | Next-action fitness |
| Sensitive attributes inferred reliably | |

### Shadow Alex vs Source Alex

[SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) scores two different objects. Do not collapse them into a compiled life.

| | Object | Feel |
| --- | --- | --- |
| **Source Alex** | Authored fixtures — messages, events, emails, relationships | A genuinely reconstructable person (fragments that read like a mystery) |
| **Shadow Alex** | Durable remainder after decay + strip | One social obligation due soon, one newly unblocked work task, one low-priority review, no urgent interrupt — useful to Alex, **boring to a detective** |

The leftover database must be a **terrible detective novel**. Enigma still understands him enough to help. Do **not** create `ALEX_BIOGRAPHY.md`; authored fixtures are the source of truth. Evaluators attack as outsiders ([SEC-07 anti-biography](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md#anti-biography-evaluators)).

**Time depth:** Source Alex is expanding from three January weeks to **six months of ordinary events** (2026-01 → 2026-06) as a version bump of `scenarios/alex-v1/` — not a biography file and not a second package ([demo-corpus.md](./demo-corpus.md#six-month-ordinary-life-d08f) · [D08f](../../tickets/demo-scenario/D08f-alex-six-month.md)). SEC-07’s intended steal point is a **June 30** snapshot after live Jan–Jun + decay: attacker reconstructs vs Enigma still useful. Thesis: biography decays faster than utility. D08f authors events; [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) owns the attacker.

### Prompt continuity vs world continuity

Context compilation ([ADR-029](../adr/029-context-compilation-request-shaped-memory.md)) is the conversational mechanism that matches this retention model.

By June 30:

- **PROMPT CONTINUITY** Jan–Jun: almost none
- **WORLD CONTINUITY** Jan–Jun: selectively preserved

“What happened with that thing I was waiting on?” is answerable because the world transition survived, not because the hosted model kept six months of transcripts.

“What exact words did Maya use in February?” may be impossible because the raw source expired. **That is not memory failure. That is successful forgetting.**

Words are working memory. State is memory. Once conversation has safely changed structured state, the words that caused the change should usually become disposable.

D08f can later test three independent curves (do not author the six-month corpus here):

```text
                 time →
raw recoverability     ███████▃▁
dialogue recoverability████▂▁▁▁
world utility          █████████
```

SEC-07 still scores biographical reconstruction ↓ while executive-function utility remains ↑. Compilation is how the conversational side refuses to recreate the raw/dialogue curves on the wire.

## Reconstructability budget (per persistent field)

Before adding or retaining any durable field, apply the checklist from [ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md):

| Risk | Durable shadow rule |
| --- | --- |
| Identity (name, employer, handle) | Do not persist |
| Exact content | PRIVATE_RAW + short TTL only |
| Exact time / place / amount | Bucket or derive ([derived attributes](#derived-attributes-nist-precedent)) |
| Cross-context relationship linkage | Purpose-scoped alias — not global graph |
| Behaviour / sensitive inference | No permanent pilot storage |

**Durable schema:** NO raw prose · NO exact geography · NO exact financial · YES opaque relationships · YES state transitions · YES coarse temporal · YES actionability enums · source refs encrypted/separate · YES lineage fields.

## Derived attributes (NIST precedent)

Prefer derived properties over underlying values in **pseudonymous shadow** (same principle as remote egress minimisation — [ADR-012](../adr/012-reasoning-value-gate-decision.md), [privacy-model.md](./privacy-model.md)):

| Source datum | Durable shadow property |
| --- | --- |
| Exact time | `due_bucket`, `age_bucket`, `free_window_minutes` |
| Exact location | `travel_time_minutes`, `coarse_region` |
| Exact money | Amount band enum |
| Email prose | `response_expected`, `importance`, obligation state enums |

Trend toward **enums and coarse numeric dimensions** over prose. Trade-off: Enigma cannot answer *"what did they say?"* from shadow alone — must reopen source (within TTL) or re-fetch provider.

## Three retention zones

| Zone | Contains | Stance |
| --- | --- | --- |
| **Green** | Current commitments, minimal contact identities, upcoming calendar horizon, recent source evidence needed for active obligations | Purposeful working state — default persist while relevant |
| **Amber** | Months of raw email, full social graph, historic messages, embeddings, inferred preferences | Strong justification + explicit expiry; never indefinite by default |
| **Red** | Permanent mailbox archive, location history, health, finance, attachments retained indefinitely, behavioural inferences cross-linked forever | Shadow copy of person — **avoid** |

Green zone data may persist in the encrypted vault while it serves active attention and obligation reasoning. Amber zone requires TTL, user-visible justification, and periodic review. Red zone patterns are **out of scope** for v0-real pilot unless explicitly re-approved with a separate ADR amendment.

## Pilot retention defaults

Aggressive defaults; user-configurable per class in non-secret `config.json`. Gmail (and other providers) remain **archive of record** — Enigma caches, it does not replace. **EXPIRY ≠ LOSS OF ALL UTILITY:** dropping PRIVATE_RAW (including a WhatsApp quote body) must not erase independently justified derived state ([C05e](../../tickets/conversational-ui/C05e-recent-source-queries.md) · Demo `RAW_TTL` in `demo_chat.py`).

| Data class | Classification | Default retention | Zone |
| --- | --- | --- | --- |
| OAuth refresh tokens | SECRET | Persistent (Keychain) | Green |
| Raw email bodies | PRIVATE_RAW | **7 day** local cache max (pilot); no indefinite | Amber |
| Raw chat bodies | PRIVATE_RAW | **7 day** local cache max (pilot); quote unavailable after TTL | Amber |
| Attachments | PRIVATE_RAW | **Do not persist** by default; lazy fetch; delete temp after parse | Amber |
| Active obligations | PRIVATE_DERIVED | Persist while relevant (open / blocking) | Green |
| Resolved obligations | PRIVATE_DERIVED | **30–90 days** then discard or compress to minimal audit stub | Green → Amber |
| Calendar events | PRIVATE_RAW / DERIVED | Limited recent horizon (upcoming + short past window) | Green |
| People / contacts | PRIVATE_DERIVED | Stable identity + alias + **minimal** relationship state — **not** full correspondence history | Green |
| Embeddings / FTS / vector index | PRIVATE_DERIVED | **Expire with source**; reproducible from retained facts, not precious | Amber |
| Interaction-frequency aggregates | PRIVATE_DERIVED | **Expire with source** or decay to coarse buckets | Amber |
| Inferred relations | PRIVATE_DERIVED | Lineage-bound; cascade on forget | Amber |
| Tone memory (style enums) | PRIVATE_DERIVED_PREFERENCE | USER-SET until revised; LEARNED until unreinforced decay; never conversation logs | Green → Amber |
| Cached retrieval chunks | PRIVATE_DERIVED | **Expire with source** | Amber |
| Source-derived features | PRIVATE_DERIVED | Lineage-bound; purpose-scoped | Amber |
| Historical audit material | audit/ | Scoped to active justification; no indefinite biography audit | Green → Amber |
| Remote LLM payloads | — | **No content persistence**; hash / field counts / audit disclosure only | — |
| Egress disclosure records | audit/ | Per SEC-02 audit policy | Green |

Extended table and enforcement notes: [SEC-01](../../tickets/security/SEC-01-secrets-encrypted-storage.md), [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md).

## Sensitive inferences (special class)

Do **not** infer-and-store permanently:

- Medical / health
- Sexuality
- Political affiliation
- Substance use
- Intimate relationships
- Financial distress
- Behavioural routines (commute, sleep, location patterns)

**Temporary relevance** for answering a user question is acceptable — persistent sensitive memory requires a **higher bar** and eventual explicit user approval.

> **Derived data can be MORE sensitive than originals.**

A single benign email thread plus calendar pattern can imply health or financial stress. Deletion and forget operations must remove **derived state** (summaries, embeddings, inferred labels, graph edges) — not only raw MIME blobs.

A late reply is **not** a persistent label of depressed, cheating, or financially distressed ([ethics.md](./ethics.md)).

Pilot invariant: **no permanent storage of sensitive inference classes** ([SEC-05 Q14](../../tickets/security/SEC-05-personal-data-pilot-gate.md)).

**Tone memory is not a loophole.** Communication-style enums (`verbosity=LOW`, `formality=CASUAL`) are an allowed `PRIVATE_DERIVED_PREFERENCE` subclass — *how to speak*, inspectable and correctable ([ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [tone-memory.md](./tone-memory.md)). Personality, persuadability, self-esteem, and political labels inferred from discourse are the same ban as the list above. A frustrated turn is TURN-LOCAL and evaporates; it must not become “user is irritable.” The Amber-zone phrase “inferred preferences” means unbounded behavioural inference — not this closed style-enum object. Conversation logs are not retained as style evidence.

Inspectable tone: *"How do you think I like you to talk to me?"* is a sibling of *"What do you remember about me?"* — then the user corrects.

## User-facing forget operations (future first-class)

Product operations planned as first-class APIs (implementation: [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md)):

| Operation | Effect |
| --- | --- |
| **"What do you remember about me?"** | Inspectable inventory of retained classes and scopes (not raw dump) |
| **"How do you think I like you to talk to me?"** | Inspectable tone-memory profile (style enums only); user may correct ([ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md)) |
| **"Why are you remembering that?"** | Provenance link: source id, retention reason, expiry, lineage |
| **"Forget everything about that project / person / before June"** | Graph operation: blobs + SourceRecords + all derived rows + embeddings + aggregates + inferred relations + cached chunks for matching scope |

Forget is not "hide from UI" — it is **cryptographic / structural deletion** inside the vault with cascade to all derivatives that lack independent justification.

## Regulatory alignment (brief)

Enigma retention design aligns with common data-minimisation principles — not legal advice:

- **ICO storage limitation** ([UK GDPR principle](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-protection-principles/a-guide-to-the-data-protection-principles/storage-limitation/)): retain personal data only while necessary for the stated purpose; periodic review; erase when purpose expires. **Pseudonymised data remains personal data** if re-identification is possible — Enigma's PRIVATE_DERIVED graph can re-identify while mappings exist; treat it accordingly. **Scoped aliases** ([ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md)) reduce cross-context linkability in the data estate; the identity resolver holds equivalence separately ([packages/identity](../../packages/identity)).
- **NIST Privacy Framework** ([Identify-P / Control-P](https://www.nist.gov/privacy-framework)): minimise data collected and disclosed; prefer derived answers over transmitting or retaining complete underlying values.

Full security boundary: [ADR-021](../adr/021-personal-data-security-boundary.md). Vault implementation: [ADR-022](../adr/022-private-vault-storage.md). Pseudonymous shadow shape: [ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md). Tone memory (style, not dossier): [ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md). Ethics creed (user is subject, never raw material): [ethics.md](./ethics.md) · [ADR-026](../adr/026-ethics-creed-user-is-subject.md).
