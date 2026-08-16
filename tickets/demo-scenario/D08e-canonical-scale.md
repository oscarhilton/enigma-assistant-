# D08e — Canonical scale profile (empirical curves)

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D08e-canonical-scale` |
| Domain | `demo-scenario` / `demo-evaluation` |
| Parent | [D08](./D08-canonical-alex.md) |

## Question

At what background volume does the apparatus sweat — embedding pollution, naïve O(n), memory growth, prompt/context bloat, excessive premium routing — **without** requiring a “benchmark MacBook heater”?

Canonical target: **~5k** background messages. The deliverable is the **shape of the curves**, not another green checkbox.

## Package boundary (hard)

- May edit: alex-v1 `canonical` / `stress` profiles, corpus fingerprints in eval reports
- May edit: D07 scale metrics + curve artefacts (JSON/CSV under eval outputs)
- Must not: download 115k FinePersonas in PR CI (nightly/manual only)
- Must not: make interactive `demo` profile stress-sized by default

## Hard depends

- D08c, D08d
- D07 metrics extensions
- D11 scale replay fixtures (soft if offline replay not needed for all points)

## Soft depends (~)

- D10 suppression dashboard

## Unlocks / enhances

- Phase 2.5 exit criterion (5k plausible background + realistic noise)
- Decision point for **Shadow Mode** (stop expanding Demo Mode)

## Non-goals

- Replacing interactive demo with 25k inbox
- Architectural rewrites for cleverness; fix only measured cliffs

## Scale ladder

Run approximately (PR CI: small points only; nightly/manual: mid; stress: manual):

| N messages | Role |
| --- | --- |
| 100 | smoke |
| 500 | early shape |
| 1,000 | CI-friendly mid |
| 2,500 | pre-canonical |
| **5,000** | **canonical target** |
| 10,000 | stretch |
| 25,000 | stress only — not normal CI |

## Graph (artefacts required)

For each N, record:

- index size
- ingest time
- retrieval latency
- Recall@K
- precision
- remote calls
- cost

**Look for shape:** gentle latency growth with flat recall is success. A Recall@10 cliff around ~3k is more valuable than a green ticket — file a finding, don’t hide it.

## Acceptance criteria

- [ ] Canonical profile ~5k background + ~1–2k noise (D08d)
- [ ] Ladder runs produce graphable artefacts for the metrics above
- [ ] Storyline / critical recall under noise still gated (≤1 pp vs spine at canonical N)
- [ ] Corpus fingerprint on every eval report
- [ ] Stress profile (10k/25k) documented for manual runs only
- [ ] Written note on curve shape (flat / cliff / cost blow-up) attached to PR or `docs/`

## Test plan

- Nightly canonical A/B at 5k; PR uses mini + maybe 100/500
- Embedding index size + retrieval latency sampled at 1k / 5k minimum

## Privacy constraints

- Public Demo remains `SYNTHETIC_CONFIRMED` only; no Private credentials
