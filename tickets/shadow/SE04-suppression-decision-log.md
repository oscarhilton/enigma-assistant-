# SE04 — Suppression decision log + frozen snapshots

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE04-suppression-decision-log` |
| Domain | `shadow` |
| Baseline | [shadow-silence-evaluation.md](../../docs/architecture/shadow-silence-evaluation.md) · [ADR-009](../../docs/adr/009-silence-as-prediction.md) |

## Package boundary (hard)

- May edit: `packages/evaluation/**` and/or `packages/attention/**` for decision-log schema + writer
- May edit: `apps/api/**` / `apps/worker/**` only for thin persist hooks under Shadow root
- May amend: `docs/architecture/shadow-silence-evaluation.md`, stub JSON under `docs/architecture/shadow-eval-stubs/`
- May edit: matching tests
- Must **not** edit: `EnvironmentMode` / simulation env (S01), Demo UI / demo attention routes, Gmail OAuth
- Must **not** ship full Shadow accuracy UI (SE09)

## Hard depends

- None for schema + fixture tests

## Soft depends (~)

- S01 `done`
- S02 Shadow storage root
- S04 attention log (reuse candidate ids when present)
- SE01 / SE02 subject refs
- SE05–SE08 consumers

## Unlocks / enhances

- Replayable silence predictions for audits, day freeze, miss reconstruction
- Feeds SE06 stratified samples and SE08 metrics

## Non-goals

- Treating behavioural mismatch as auto-failure
- Changing attention ranking thresholds (log only)
- Demo ground-truth scoring

## Acceptance criteria

- [ ] Schema for frozen suppression decision matching stub (`decision`, `decided_at`, `candidate`, `available_evidence`, `retrieval_snapshot`, `priority`, `confidence`, `threshold`, `reason_codes`)
- [ ] Writer path records **every** `SUPPRESS` (and documents whether `SURFACE` is also logged)
- [ ] Snapshots store refs only — no wholesale Notes / raw mail bodies
- [ ] Replay helper loads original evidence refs without requiring “current” store state to equal past
- [ ] Tests: serialize/deserialize; hostile path never writes under Demo root
- [ ] Cross-link from silence-evaluation doc + ADR-009

## Test plan

- Golden fixture equals `suppression_decision.v0.json` shape
- Writer under tmp Shadow root; assert Demo path untouched

## Privacy constraints

- Artefacts stay on Shadow/Private roots
- Prefer PERSON_* / transformed refs in any export
