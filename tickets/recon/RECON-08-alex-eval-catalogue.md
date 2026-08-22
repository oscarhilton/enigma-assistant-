# RECON-08 — Alex eval catalogue

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/RECON-08-alex-eval-catalogue` |
| Domain | `recon` / `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/**` catalogue loaders, evaluator-only YAML under evaluation/`ground_truth` (not timeline), [life_position.v0.json](../../docs/architecture/eval-stubs/life_position.v0.json) only if additive and PolarIS-compatible, tests, this ticket
- Must not edit: `scenarios/alex-v1/timeline/**`; PolarIS searcher; N01 scorer replacement; Observatory probes (03)

## Hard depends

- [RECON-07](./RECON-07-life-scripts.md) `done`

## Soft depends (~)

- [R01](../reasoning/R01-scenario-truth-catalogue.md) support contracts if present on `main` — reuse ids, do not ingest at runtime
- [ALEX-EVAL-01](../demo-evaluation/ALEX-EVAL-01-life-positions.md) (`future`, PolarIS-gated) — this catalogue is the **earlier** general list; ALEX-EVAL-01 may cite it later
- [C12](../conversational-ui/C12-life-scripts.md) as sources of moments

## Unlocks / enhances

- OBSERVATORY-03 probe targets; ALEX-EVAL-01/02

## Intent

A replayable **Alex eval catalogue**: clocked situations + invariants, never one golden move, never a life score. First visible catalogue for Observatory Alex-benchmark integration (panel hook in 02; live probes in 03).

## Non-goals

- PolarIS tournament (ALEX-EVAL-02)
- Hugging Face Level 2
- Moral ranking of Alex
- Editing Demo fake mail unless a tiny eval YAML is required

## Acceptance criteria

- [ ] ≥5 motif or support-contract families load without Enigma ingest
- [ ] Each entry: clock + invariants (`must_consider` / `must_not_recommend` or R01 equivalent)
- [ ] Positions absent from simulation ingest payloads
- [ ] Observatory can list catalogue ids as **specified/verified eval fixtures**, not as `USABLE` product features
- [ ] No collision: PolarIS-only fields remain optional until ALEX-EVAL-01

## Exit conditions

Done when OBSERVATORY-03 can attach a probe to at least one catalogue id, and ALEX-EVAL-01 can cite the same ids without forking a second Alex.

## Test plan

- Schema validate catalogue
- Negative: ingest path does not see catalogue files
- Replay stability: compile twice → same id

## Privacy constraints

- Evaluator-only; never LLM prompt corpus
- Demo never shares Private roots ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))
