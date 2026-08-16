# D08b — Background corpus pipeline

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/D08b-corpus-pipeline` |
| Domain | `demo-scenario` / `demo-simulation` |
| Parent | [D08](./D08-canonical-alex.md) |
| PR | (pending) |

## Package boundary (hard)

- May edit: `packages/simulation/src/personal_enigma/simulation/corpus/**`
- May edit: `packages/simulation/tests/fixtures/corpus/**`, corpus tests
- May edit: docs under `docs/architecture/demo-corpus.md`, ADR-007
- May extend: `SyntheticMailSource` multi-stream stubs (D04 amendment)
- Must not: download FinePersonas 115k in CI; merge full Alex+corpus timelines (D08c)

## Hard depends

- D08a (canonical spine)
- D04 synthetic mail surface

## Soft depends (~)

- D06 `ScenarioSignalClass`
- D03 background schema (full validation can follow)

## Unlocks / enhances

- D08c background integration
- Feature scenarios in §80–81

## Non-goals

- Canonical recall A/B at 5k messages (D08e)
- Public redistribution of derived FinePersonas subsets without licence review

## Acceptance criteria

- [x] CorpusAdapter protocol + CorpusMessage/CorpusConversation (no Enigma obligation fields)
- [x] Manifest, registry, cache, selectors, sanitise, timeline, safety
- [x] Working FinePersonas adapter against `finepersonas-mini` (+ optional HF fetch behind `--force-network`, never CI)
- [x] Full sanitiser: identity/domain/URL rewrite, secret scan, provenance `SYNTHETIC_CONFIRMED`
- [x] Seeded conversation selection (not message sampling); deterministic timeline placement
- [x] Derived cache under configurable root (`ENIGMA_CORPUS_DERIVED` / `--derived-root`)
- [x] CLI: `enigma corpus list|fetch|inspect|sanitise|sample|verify|build` functional on mini fixture
- [x] 100 imported conversations replay deterministically via mini expansion (no 115k download in CI)

## Test plan

- Unit tests on mini fixture only (no network corpus download)
- Public-demo provenance gate
- Sanitiser drops generation metadata keys; rejects secret-like strings; rewrites domains/URLs
- 100-conversation expand → build → SyntheticMailSource fingerprint equality

## Privacy constraints

- Public Demo: `SYNTHETIC_CONFIRMED` only ([ADR-007](../../docs/adr/007-demo-corpus-provenance.md))
- Cache under `~/.cache/enigma/datasets/` (override via `ENIGMA_CORPUS_CACHE`); derived under `datasets-derived/`; never share Private roots
