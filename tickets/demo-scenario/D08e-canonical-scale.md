# D08e — Canonical scale profile

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/D08e-canonical-scale` |
| Domain | `demo-scenario` / `demo-evaluation` |
| Parent | [D08](./D08-canonical-alex.md) |

## Package boundary (hard)

- May edit: alex-v1 `canonical` / `stress` profiles, corpus fingerprints in eval reports
- May edit: D07 scale metrics (suppression, compression, cost/1k, embedding pressure)
- Must not: download 115k FinePersonas in PR CI (nightly/manual only)

## Hard depends

- D08c, D08d
- D07 metrics extensions
- D11 scale replay fixtures

## Soft depends (~)

- D10 suppression dashboard

## Unlocks / enhances

- Phase 2 “attention under noise” claim
- D12 “thousands in, two things out” sequence

## Non-goals

- Replacing interactive `demo` profile with stress-sized inbox

## Acceptance criteria

- [ ] Canonical profile ~5k background + ~1–2k noise
- [ ] Quality / performance / privacy / cost inside Phase 2 targets
- [ ] Storyline recall under noise gated (≤1 pp critical-recall degradation)
- [ ] Corpus fingerprint recorded on every eval report
- [ ] Stress profile documented for manual runs only

## Test plan

- Nightly canonical A/B; PR uses mini fixture only
- Embedding index size + retrieval latency sampled at 1k / 5k

## Privacy constraints

- Public Demo remains `SYNTHETIC_CONFIRMED` only; no Private credentials
