# D08b — Background corpus pipeline

| Field | Value |
| --- | --- |
| Status | `in_progress` (scaffolding only — foundation PR) |
| Branch | `ticket/corpus-background-integration` |
| Domain | `demo-scenario` / `demo-simulation` |
| Parent | [D08](./D08-canonical-alex.md) |

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
- [x] Manifest, registry, cache, selectors, sanitise, timeline, safety stubs
- [x] finepersonas / mbox / maildir adapter stubs
- [x] Mini fixture `finepersonas-mini` (2–3 original synthetic conversations; not HF download)
- [x] CLI stubs: `enigma corpus list|fetch|inspect|sanitise|sample|verify`
- [x] Hard invariants tested: public demo rejects non-`SYNTHETIC_CONFIRMED`; seeded selection deterministic; generation metadata stripped; `signal_class` never on mail items
- [ ] Full FinePersonas fetch + 100-conversation deterministic replay (follow-up; not PR CI)

## Test plan

- Unit tests on mini fixture only (no network corpus download)
- Public-demo provenance gate
- Sanitiser drops generation metadata keys

## Privacy constraints

- Public Demo: `SYNTHETIC_CONFIRMED` only ([ADR-007](../../docs/adr/007-demo-corpus-provenance.md))
- Cache under `~/.cache/enigma/datasets/`; never share Private roots
