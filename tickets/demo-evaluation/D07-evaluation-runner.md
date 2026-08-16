# D07 — Evaluation runner

| Field | Value |
| --- | --- |
| Status | `done` (merged #32) |
| Branch | `ticket/D07-evaluation-runner` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/**` (runner, metrics, regression, report)
- May add CLI entrypoints under `packages/evaluation` or `apps/api` scripts — declare in PR
- Must not edit: scenario corpus (D8), demo UI (D10)

## Hard depends

- D1, D6

## Soft depends (~)

- D5

## Unlocks / enhances

- CI regression gates for Demo Mode
- Model/provider comparison reports

## Non-goals

- Capturing live provider replays (D11)
- Authoring Alex timeline (D8)

## Acceptance criteria

- [x] Metrics modules: attention, privacy, memory, retrieval, cost
- [x] Single command produces a complete scenario report
- [x] Critical recall / precision / duplicates / stale alerts / privacy / cost covered at least as stubs with real attention+privacy wired

### Amendment — noise / scale metrics (plan §85)

- [x] Background suppression rate
- [x] Background false alerts / 1k messages
- [x] Attention compression ratio
- [x] Storyline recall under noise (A/B) — D08c + D08e displacement / noise arm
- [ ] Retrieval pollution / canonical evidence recall@K
- [x] Remote calls + cost per 1k inbound signals
- [x] Corpus fingerprint on reports
- [x] Cost per simulated month stub + remote reasoning rate alias (F-eval-noise-metrics)

## Test plan

- [x] Smoke run on tiny scenario fixture
- [x] Report JSON/Markdown schema snapshot test
- [x] Mini-fixture A/B report includes suppression + compression fields

## Privacy constraints

- Reports must not embed Private Mode data; Demo root only

## Notes

- CLI entrypoint: `enigma-eval` (`uv run enigma-eval`) → `reports/<run_id>/`
- Soft-merged D06 ground-truth models/loader/fixtures so the runner can score missed obligations before D06 lands on main
