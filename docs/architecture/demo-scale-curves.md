# Demo Mode — Canonical scale curves (D08e)

**Status:** understood behaviour first; no premature SLOs  
**Related:** [demo-corpus.md](./demo-corpus.md), [D08e](../../tickets/demo-scenario/D08e-canonical-scale.md)

## Question

At what background volume does the apparatus sweat — embedding pollution,
naïve O(n), memory growth, prompt/context bloat, excessive premium routing —
**without** requiring a “benchmark MacBook heater”?

Canonical target: **~5k** background messages (+ ~1.5k machine noise, D08d soft).

## Profiles (message budgets)

| Profile | Background | Noise (D08d soft) | CI load? |
| --- | --- | --- | --- |
| `feature` | 0 | 0 | yes (empty) |
| `demo` | ~1k intent / **8** CI | ~250 | yes (small) |
| `canonical` | **~5 000** | **~1 500** | **no** — documented + nightly |
| `stress` | **25 000** (stretch 10k) | ~5 000 | **never** — manual only |

PR CI must not download FinePersonas (~115k). Ladder smoke uses
`finepersonas-mini` + deterministic `expand_conversations`.

## Ladder

| N | Role | Where |
| --- | --- | --- |
| 100 | smoke | PR CI |
| 500 | early shape | PR CI |
| 1 000 | CI-friendly mid | optional / nightly |
| 2 500 | pre-canonical | nightly |
| **5 000** | **canonical** | nightly / manual |
| 10 000 | stretch | manual |
| 25 000 | stress | manual only |

Artefacts: `scale_ladder.json` + `scale_ladder.csv` via
`personal_enigma.evaluation.scale_ladder` (`run_scale_ladder` /
`write_scale_ladder_artefacts`).

Metrics per point: index size, ingest time, retrieval latency, Recall@K,
precision, remote calls, cost, compression ratio, suppression,
false alerts / 1k, cost & remote calls per 1k. Every report carries a
**corpus fingerprint** (id, revision, sanitiser, seed, profile, digest).

## Curve shape note (initial CI smoke)

On the mini expand-to ladder (100 → 500), stub latency scales roughly with N
and Recall@K stays flat by construction — shape label typically
`linear_latency_flat_recall` or `roughly_linear_latency`.

This is **understood stub behaviour**, not a production SLO. When nightly
canonical (~5k) runs land with real embeddings:

- Flat Recall@K + roughly linear latency → Phase 2.5 can pass even if 5k is
  “slower than ideal”.
- A Recall@K cliff near ~3k, or cost inflection from premium routing leak →
  file a finding; do not hide it behind a green checkbox.
- Cost blow-up under noise → next optimisation belongs in routing / selection,
  not more synthetic tuning.

Shadow Mode teaches more than another week of synthetic tuning if 5k is
predictable and correct.

## Storyline gate

Spine (A) vs spine+background (B) critical recall drop ≤ 1 pp;
`critical_displacement == 0`. Optional third arm spine+background+noise
(soft-depend D08d) uses the same ≤1 pp budget.
