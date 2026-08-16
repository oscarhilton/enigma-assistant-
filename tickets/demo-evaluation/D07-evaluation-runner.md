# D07 — Evaluation runner

| Field | Value |
| --- | --- |
| Status | `todo` |
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

- [ ] Metrics modules: attention, privacy, memory, retrieval, cost
- [ ] Single command produces a complete scenario report
- [ ] Critical recall / precision / duplicates / stale alerts / privacy / cost covered at least as stubs with real attention+privacy wired

## Test plan

- Smoke run on tiny scenario fixture
- Report JSON/Markdown schema snapshot test

## Privacy constraints

- Reports must not embed Private Mode data; Demo root only
