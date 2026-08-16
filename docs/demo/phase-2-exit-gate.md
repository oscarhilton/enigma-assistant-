# Phase 2 exit gate

Checklist for declaring Demo Mode Phase 2 complete enough to answer:

> Does continuity help — and can we show it safely on fiction first?

## Environment separation

- [x] Demo and Private storage roots never share DB / vectors / HMAC namespaces (ADR-005)
- [x] `REAL SOURCE ACCESS = IMPOSSIBLE` under Demo Mode (D01 invariant)
- [x] Injectable clock for domain time (D02 / ADR-006)

## Evaluation

- [x] Feature scenarios validate (D03)
- [x] Synthetic adapters emit source-layer records only (D04)
- [x] Simulation engine deterministic replay (D05)
- [x] Ground truth + missed-obligation detection (D06)
- [x] Eval runner report command (D07)
- [x] Alex v0.2.0 three-week benchmark corpus (D08)
- [x] Adversarial privacy packs (D09)
- [x] Demo UI chrome with banner + timeline controls (D10)
- [ ] Provider replay offline path (D11) — soft for exit; optional if sibling lands
- [x] Curated product-demo walkthrough (D12)

## What Phase 2 proved

- Enigma can run the **real** pipeline against a fictional life with known truth.
- Continuity artefacts (open loops across weeks) can be evaluated and demonstrated.
- Privacy invariants can be exercised under adversarial scenario packs without Private data.

## Explicitly out of scope

- Production readiness for real Private lives without separate sign-off
- Mail/Messages depth beyond current adapters
- Claiming hosted-model necessity (remote remains optional)
- Public marketing site / launch
