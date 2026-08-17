# ADR-023: Persistent Shadow — Abstract State, Not Biography

**Status:** Accepted  
**Date:** 2026-08-17

## Context

[ADR-022](./022-private-vault-storage.md) specifies **where** and **how long** Private data persists — encrypted vault layout, classification (SECRET · PRIVATE_RAW · PRIVATE_DERIVED · REMOTE_SAFE · PUBLIC), retention zones, and memory decay. [data-retention.md](../architecture/data-retention.md) asks the **red-line reconstructability test**: if all original sources were lost tomorrow, could someone reconstruct "quite a lot" of the user's life from Enigma alone?

That test governs **volume and lifetime** of retention. It does not yet specify the **shape** of durable memory: what a stolen `vault.db` (without keys, identity mappings, or raw cache) *looks like* to a motivated analyst.

The expanded design target:

> **The ideal Enigma database has enormous behavioural utility while being astonishingly poor as a biography.**

Enigma stores an **index of what matters**, not **your life**. Gmail and calendar are archives of record; Enigma is working memory for unresolved obligations, dependencies, attention, and next actions.

**Terminology:** **Persistent shadow** (this ADR) is the **representation shape** of durable `PRIVATE_DERIVED` state in the encrypted vault — opaque IDs, coarse properties, purpose-scoped graphs. It is **not** the same as **Shadow Mode** ([ADR-008](./008-shadow-storage-roots.md)), which is a separate Phase 3 storage root and runtime mode. Private vault durable memory follows persistent-shadow rules; Shadow Mode inherits them when it lands.

**Regulatory caveat (honest):** Persistent shadow is **pseudonymised personal data** under ICO guidance while Enigma holds re-identification mappings and keys — not truly anonymous. The target is **meaningless enough** that a stolen shadow layer alone (without source mappings, HMAC keys, identity resolver, or raw blob cache) does not reveal the person. See [data-retention.md — Regulatory alignment](../architecture/data-retention.md#regulatory-alignment-brief).

## Decision

### Core design target

The persistent store is a **semantically useful but personally meaningless shadow**. If the shadow DB leaks **without** source mappings and keys, it should read like an **abstract state machine** — obligations, blockers, availability windows, dependency edges — not a reconstructable biography.

Philosophy shift:

```text
BAD mental model:  Enigma = second archive of my life
GOOD mental model: Enigma = durable index of what still matters
```

### Four-layer lifecycle (canonical)

Evidence flows through four representation layers. FORGET is a terminal state — not merely TTL expiry on lower layers.

```text
SOURCE WORLD (raw · identifiable · short-lived)
  email / calendar / messages / notes
        │
        │ extract
        ▼
ACTIVE PRIVATE STATE (purpose-bound — only what Enigma currently needs)
  obligations · blockers · availability · evidence refs · typed transitions
        │
        │ decay — detail↓ precision↓ linkability↓ utility retained
        ▼
PSEUDONYMOUS SHADOW (enums · buckets · state transitions · low narrative reconstructability)
  durable working memory — PRIVATE_DERIVED rows in encrypted vault.db
        │
        │ expiry — recoverability → zero within Enigma
        ▼
FORGET
```

| Layer | Identifiability | Lifetime | Classification |
| --- | --- | --- | --- |
| **Source world** | High (names, prose, exact timestamps) | Short — RAW cache TTL ([ADR-022](./022-private-vault-storage.md)) | PRIVATE_RAW blobs |
| **Active private state** | Medium (typed facts may still carry labels) | While purpose-bound and relevant | PRIVATE_DERIVED (active) |
| **Pseudonymous shadow** | Low (opaque IDs, enums, buckets) | Until justification expires | PRIVATE_DERIVED (durable shape) |
| **Forget** | N/A — recoverability → zero | Terminal | Deleted |

**DECAY ≠ FORGET:** DECAY compresses active state into shadow form while retaining utility. FORGET removes recoverability entirely. "Forget this person" must **not** mean "replace name with `PERSON_Q7` and keep everything forever."

Memory decay ([SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md)) applies across **active private state** and **source world** — progressive abstraction into shadow form, then FORGET when justification expires.

### Good vs bad persistent representations

**BAD (reconstructive):**

```text
"Joe Atkinson annoyed with Oscar about Believ charger rollout; wants response by Friday"
```

**GOOD (shadow):**

```text
OBLIGATION_81
  actor=SELF
  related_entity=PROJECT_R9
  due_bucket=WITHIN_3_DAYS
  response_expected=YES
  importance=ELEVATED
  source_evidence=SOURCE_9182   # encrypted ref; body in separate blob store
```

Durable schema trends:

| Avoid in persistent shadow | Prefer in persistent shadow |
| --- | --- |
| Raw prose, subject lines, display names | Opaque entity IDs, enum states |
| Exact timestamps, geocoordinates | Time buckets, `free_window_minutes`, coarse region |
| Exact amounts | Money bands |
| Global stable person handles across all contexts | Purpose-scoped aliases (see below) |
| Inline email / note body text | Encrypted `source_id` / `blob_ref` only |

### Derived attributes (NIST precedent)

Do not persist the underlying datum when a **derived property** suffices for attention and obligation reasoning — aligned with NIST Privacy Framework *Control-P* (minimise collected and disclosed; prefer derived answers over complete underlying values). Same principle as remote egress transformation ([ADR-012](./012-reasoning-value-gate-decision.md) privacy transform discipline; [privacy-model.md](../architecture/privacy-model.md)):

| Source datum | Durable shadow property |
| --- | --- |
| Exact time | `due_bucket`, `age_bucket`, `free_window_minutes` |
| Exact location | `travel_time_minutes`, `coarse_region` enum |
| Exact money | Amount band enum |
| Email prose | `response_expected`, `importance`, `age_bucket`, obligation state enums |

Trend toward **enums and coarse numeric dimensions** over prose in durable shadow. Re-fetch or re-read source (within TTL) when the user asks *"what did they actually say?"* — that is the intended trade-off.

### Lineage (formal, lightweight)

Shadow and active-state records carry lineage metadata enabling deterministic forget as a **graph operation**:

| Field | Example | Purpose |
| --- | --- | --- |
| `derived_from` | `[SRC_123, SRC_188]` | Source dependency graph |
| `purpose` | `OPEN_LOOP_TRACKING` | Why this record exists |
| `retention_class` | `ACTIVE_UNTIL_RESOLVED` | When justification ends |
| `expires_after_resolution` | `30d` | Post-resolution TTL |

`forget(SRC_123)` answers:

- What depends **exclusively** on this source?
- What has **independent evidence**?
- What **must disappear**?
- What can **remain but lose confidence**?

"Forget everything about X" is a graph operation — not best-effort DB delete.

### Graph linkability risk (ICO-motivated intruder)

Stable HMAC `PERSON_*` aliases forever create a **permanent linkage handle** — pseudonymised data remains personal data if graphs can re-identify ([data-retention.md](../architecture/data-retention.md)). Mitigation: **scoped aliases**, not one global identity graph.

| Scope | Example alias | Links across scopes? |
| --- | --- | --- |
| Within project | `PERSON_D4` | No — distinct from social context |
| Within social context | `PERSON_P8` | No |
| Per remote request | `PERSON_X2` | Ephemeral; discarded after egress |

A **secure identity resolver** ([packages/identity](../../packages/identity)) knows equivalence when required for local reasoning; the **data estate does not auto-link** across scopes. Move from **one global graph** → **several purpose-scoped graphs** + resolver when equivalence is needed.

Current `EntityResolver.resolve_person()` returns stable `PERSON_*` pseudonyms — acceptable for remote-safe transform ([privacy-model.md](../architecture/privacy-model.md)); durable vault storage should adopt **scope-aware alias namespaces** as SEC-06 / identity work lands. See [personal-data-security.md — Persistent shadow](../architecture/personal-data-security.md#persistent-shadow-representation).

### Reconstructability budget (per persistent field)

Before adding or retaining any durable field, score reconstructability risk:

| Question | If yes → |
| --- | --- |
| Does it reveal identity (name, employer, handle)? | Red zone — do not persist in shadow |
| Does it preserve exact content? | Keep in PRIVATE_RAW with short TTL only |
| Does it preserve exact time / place / amount? | Bucket or derive |
| Does it reveal relationship identity across contexts? | Scope alias or omit edge |
| Does it enable behaviour-pattern inference (routine, health)? | Sensitive inference class — no permanent pilot storage ([ADR-022](./022-private-vault-storage.md)) |
| Does it enable sensitive inference (medical, financial distress)? | Reject or ephemeral answer-only |

**Durable schema checklist:** NO raw prose · NO exact geography · NO exact financial values · YES opaque relationships · YES state transitions · YES coarse temporal buckets · YES actionability / importance enums · YES dependency graph · source refs **encrypted and separate** (SourceRecord + blob_ref pattern).

### Shadow benchmark — dual metrics (acceptance benchmark)

First-class security metric **before Gmail pilot** ([SEC-05 Q16](../../tickets/security/SEC-05-personal-data-pilot-gate.md), [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md)):

1. Populate Alex (or equivalent) Private fixture DB through normal ingest + decay pipelines.
2. Strip keys, identity mapping tables, credentials, and PRIVATE_RAW blob cache.
3. Hand remainder to a motivated analyst or model.
4. Score **reconstructability ↓** and **utility ↑** independently.

**Research question:** *How much biography can we destroy before Enigma stops being useful?*

**Target curve:** personal reconstructability collapses **faster** than executive-function usefulness.

| Reconstructability metric (→ **0**) | Utility metric (→ **high**) |
| --- | --- |
| Real names recovered | Attention fidelity |
| Specific message content recovered | Open-loop fidelity |
| Employers / named projects recovered | Dependency fidelity |
| Precise locations recovered | Next-action fitness |
| Sensitive attributes inferred reliably | |

**FAIL** if biography reconstructs while utility is high enough to matter — or if utility collapses before reconstructability does. **PASS** if reconstructability → 0 while utility metrics remain high.

**Shadow Alex vs Source Alex:** Source Alex (authored fixtures) is a reconstructable person. Shadow Alex (durable remainder) should be useful working memory and a **terrible detective novel** — not a recognisable life. Do not author `ALEX_BIOGRAPHY.md`; evaluators attack as outsiders. See [data-retention.md](../architecture/data-retention.md#shadow-alex-vs-source-alex) · [SEC-07 detective-novel criterion](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md#detective-novel-criterion-the-mystery-of-alex-morgan).

### Trade-off (document honestly)

More abstract shadow → Enigma **cannot** answer *"what did Joe want?"* or *"what exactly did that email say?"* without reopening source (within RAW cache TTL or provider re-fetch). That is the **right trade**:

- Gmail / calendar = archives
- Enigma = what's unresolved, depends on what, changed, matters, possible now, and what is worth forgetting

Product copy and conversational tools must not imply Enigma remembers prose it deliberately discarded from durable shadow.

> **Enigma deliberately forgets narrative detail while preserving enough state to remain useful.**

### Relationship to ADR-022 classification

This ADR **does not change** the [ADR-022](./022-private-vault-storage.md) classification model:

- Source bodies remain **PRIVATE_RAW** (encrypted blobs, short TTL).
- Durable obligation / graph / index rows remain **PRIVATE_DERIVED** (encrypted vault only).
- Persistent shadow specifies the **internal shape** of PRIVATE_DERIVED durable rows — not a new egress class.
- **REMOTE_SAFE** egress rules unchanged — transform before transmit ([ADR-021](./021-personal-data-security-boundary.md)).

Notes bodies remain HIGH privacy at ingest ([ADR-004](./004-notes-best-effort-no-sqlite.md)); note prose must not become durable shadow text.

## Consequences

- [data-retention.md](../architecture/data-retention.md) gains four-layer model, lineage schema, and reconstructability budget.
- [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md) decay pipeline compresses active private state → pseudonymous shadow before FORGET.
- [SEC-05 Q16](../../tickets/security/SEC-05-personal-data-pilot-gate.md) requires Shadow Reconstruction Test PASS with scored metrics.
- [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) implements the benchmark runner.
- `packages/identity` scoped-alias design is a follow-on within SEC-06 / identity tickets — resolver holds equivalence; vault graphs stay scope-local.
- Domain schema reviews (obligations, attention, people graph) must apply reconstructability budget before new durable fields.
- Tone memory ([ADR-025](./025-tone-memory-how-to-speak-not-who-you-are.md)) is a **sibling** derived object: coarse *how to speak* enums, not shadow of *who you are*. Persistent shadow must not absorb psychological traits from conversation. Style preferences are `PRIVATE_DERIVED_PREFERENCE`; inner-life labels stay under the [sensitive-inference ban](../architecture/data-retention.md#sensitive-inferences-special-class).

## Related

- [north-star.md](../architecture/north-star.md) — meaningless shadow as canonical model; privacy need not cost utility
- [ADR-022 — Private vault storage](./022-private-vault-storage.md)
- [ADR-021 — Personal data security boundary](./021-personal-data-security-boundary.md)
- [ADR-004 — Notes best-effort; no SQLite scraping](./004-notes-best-effort-no-sqlite.md)
- [ADR-008 — Shadow storage roots](./008-shadow-storage-roots.md) (Shadow **Mode** — separate from persistent shadow **representation**)
- [ADR-012 — Reasoning value gate](./012-reasoning-value-gate-decision.md) (privacy transform / derived-answer discipline at egress)
- [data-retention.md](../architecture/data-retention.md)
- [personal-data-security.md](../architecture/personal-data-security.md)
- [privacy-model.md](../architecture/privacy-model.md)
- [SEC-06](../../tickets/security/SEC-06-retention-memory-decay-forget.md) · [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) · [SEC-05 Q16](../../tickets/security/SEC-05-personal-data-pilot-gate.md)
- [ADR-025 — Tone memory](./025-tone-memory-how-to-speak-not-who-you-are.md) · [tone-memory.md](../architecture/tone-memory.md) — how to speak, not who you are
- [ADR-026 — Ethics creed](./026-ethics-creed-user-is-subject.md) · [ethics.md](../architecture/ethics.md) — minimum purpose-bound state; detective-show trap is a reconstructability FAIL
