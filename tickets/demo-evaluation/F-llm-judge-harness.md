# F — LLM Judge harness (Arm B scaffold)

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/llm-judge-benchmark` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May create/edit: `packages/evaluation/src/personal_enigma/evaluation/llm_judge/**`
- May create/edit: `packages/evaluation/tests/test_llm_judge*.py`
- May create/edit: `packages/evaluation/fixtures/llm_judge/**`
- May edit: `packages/evaluation/src/personal_enigma/evaluation/__init__.py` (exports only)
- May edit: `docs/architecture/reasoning-llm-benchmark.md`, `docs/adr/011-llm-structured-judgement.md`, ticket index / milestone pointers
- Must **not** edit: `scenarios/**/ground_truth/obligations.yaml` (sibling catalogue owns labels)
- Must **not** edit: product attention / Shadow env scaffolding

## Hard depends

- M05 (`PaygReasoningService` DISABLED / DRY_RUN / ENABLED)
- D07 evaluation package layout
- D11 replay patterns (conceptual; full Judge record/replay is a follow-up ticket)

## Soft depends (~)

- [F-judgement-scenario-catalogue](../demo-scenario/F-judgement-scenario-catalogue.md) — richer MUST_SURFACE / MUST_SUPPRESS labels; do not block on sibling `obligations.yaml` edits; use frozen fixture + TODO pointers until catalogue lands

## Unlocks / enhances

- Controlled Arm B benchmark before further Shadow investment
- [F-llm-judge-record-replay](./F-llm-judge-record-replay.md), [F-llm-judge-privacy-ablation](./F-llm-judge-privacy-ablation.md)

## Non-goals

- Live API keys in CI
- Arms C–E ([F-llm-arms-c-e](./F-llm-arms-c-e.md))
- Wiring Judge into production attention path
- Editing Alex obligation catalogue

## Acceptance criteria

- [x] Architecture doc: arms A–E, Judge-first rationale, schema, metrics, ablation, eventual architecture, parents/brunch first case
- [x] ADR-011: LLM proposes structured judgement; code decides; never raw `PrivatePerson` to hosted model
- [x] Structured judgement schema (kind/status/importance/attention/timing/confidence/reason_codes/evidence_ids) — no CoT
- [x] Code authority rejects invented evidence IDs / schema failures
- [x] Harness DRY_RUN + fixture-replay against frozen candidate+evidence payload (no network in CI)
- [x] Optional live ENABLED only when explicit developer env flag **and** key present
- [x] Tickets filed for catalogue (soft), record/replay, privacy ablation, arms C–E

## Test plan

- [x] Replay fixture yields validated judgements for parents/brunch-style candidates
- [x] Invented `evidence_ids` → authority failure
- [x] DRY_RUN never opens network; default CI path uses replay
- [x] Live path skipped unless `ENIGMA_LLM_JUDGE_LIVE=1`

## Privacy constraints

- Remote payloads are TransformedContext / PERSON_* only
- Demo fixtures only; no Private Mode data
- Privacy violations metric target: 0

## Notes

- Design: [docs/architecture/reasoning-llm-benchmark.md](../../docs/architecture/reasoning-llm-benchmark.md)
- Sibling catalogue branch (soft): expand ground truth separately; reference when merged or keep TODO
