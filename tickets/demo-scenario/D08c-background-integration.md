# D08c — Background integration

| Field | Value |
| --- | --- |
| Status | `done` (PR #46) — **scientific gate amendments complete** on `ticket/D08c-gate-hardening` |
| Branch | `ticket/D08c-background-integration` (follow-up: `ticket/D08c-gate-hardening`) |
| Domain | `demo-scenario` / `demo-simulation` / `demo-evaluation` |
| Parent | [D08](./D08-canonical-alex.md) |
| Architecture freeze | Prefer not to reopen core below **`f404597`** unless a **measured** structural failure appears. New abstractions must earn existence by explaining a measured failure. |

## Distinct failure modes (keep separate)

| Ticket | Asks |
| --- | --- |
| **D08c** | Can Enigma cope with **plausible human conversation** noise? |
| **D08d** | Can Enigma ruthlessly ignore **machine-generated sludge**? |
| **D08e** | How does behaviour **scale** (curve shape, not premature SLOs)? |

Do **not** invent D08f–D08z. Shadow Mode is **Phase 3**, designed separately.

## Package boundary (hard) — gate hardening follow-ups

- May edit: evaluation A/B comparison artefact writer, displacement metrics, pollution-trace schema
- May edit: alex-v1 spine/background profile wiring already landed in #46
- Must not: ship Enron/SpamAssassin into public Demo; promote corpus characters into meaning
- Must not: “improve the laboratory” without a measured failure motivating the change

## Merged in #46 (done)

- [x] Canonical + background merge into one chronological mailbox
- [x] Enigma cannot observe `signal_class` / background labels
- [x] Critical recall regression ≤1 pp vs spine (basic A/B)
- [x] Seeded reset reproduces identical background traffic
- [x] Background contacts remain disjoint from canonical person namespaces

## Scientific gate amendments (Phase 2.5 release requirements)

### 1. Immutable comparison artefact

A/B runs must emit a **single** comparison JSON (not two terminals to eyeball). Example shape:

```json
{
  "baseline": "alex-v1-spine",
  "treatment": "alex-v1-background",
  "git_commit": "...",
  "corpus_revision": "...",
  "sanitiser_version": "...",
  "seed": "...",
  "metrics": {
    "critical_recall": {
      "baseline": 0.97,
      "treatment": 0.965,
      "delta_pp": -0.5
    }
  }
}
```

Every metric in the A/B table below gets `baseline` / `treatment` / `delta` (or `delta_pp`). Gate pass/fail is computed from this artefact.

### 2. A/B metric table (in the artefact)

Critical recall · Precision · Duplicate rate · Stale alert rate · Canonical Recall@K · Retrieval Precision@K · Attention count · Remote calls · Input tokens · Estimated cost · Processing time

**Plus attention displacement** (catches “recall still green” misses):

| Metric | Meaning |
| --- | --- |
| Canonical attention rank (per critical item) | Rank in spine vs background |
| Mean rank delta | Average movement under noise |
| Critical item displaced below surface threshold | e.g. was #1, now #7 while UI surfaces top 3 → **functional miss** |

Identical critical recall with collapsed Retrieval Precision@K, tripled tokens, or non-zero **critical displacement** is still a failure to explain (displacement = 0 is a Phase 2.5 hard gate).

### 3. Pollution traces (evaluator-side richness)

For every canonical miss or changed decision, record retrieved docs **and match diagnostics** where available:

- rank
- source
- similarity
- entity overlap
- project overlap
- temporal relevance
- canonical/background (**evaluator-only** — never on Enigma-facing payloads)

Separates embedding similarity vs entity weighting vs temporal weighting vs relationship memory vs keyword collision.

### 4. Invariants (still required; keep tested)

1. One mailbox / identical ingestion; no Enigma-visible evaluator fields  
2. Hostile recursive serialization scan finds zero forbidden fields  
3. Disjoint identity namespaces before ingestion  
4. Deterministic seeded reset (ids, identities, timestamps, order)  
5. Background stays non-meaningful (no promoted corpus characters)

## Acceptance criteria (gate hardening)

- [x] Immutable comparison artefact written per A/B run; CI asserts `delta_pp` / displacement from file
- [x] Displacement metrics present; **critical displacement == 0** for Phase 2.5 profiles
- [x] Pollution traces include match-reason fields above (evaluator-only)
- [x] Full metric table present with baseline/treatment/delta
- [x] Artefacts retain git_commit, corpus_revision, sanitiser_version, seed

## Test plan

- [x] Golden comparison JSON schema test
- [x] Forced rank-drop fixture: recall stays 1.0, displacement fails gate
- [x] Pollution-trace schema test with evaluator-only `canonical/background` field
- [x] Existing #46 isolation / determinism tests remain green
- [x] A/B eval: alex spine only vs spine + mini/demo background
- [x] Isolation test: ground-truth metadata absent from source payloads

## Privacy constraints

- Evaluator-only classification; `.example` domains; `SYNTHETIC_CONFIRMED` only ([ADR-007](../../docs/adr/007-demo-corpus-provenance.md))
