# R-L01 — Fireworks Live Gate truth enrichments

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/R-L01-truth-enrichments` |
| Domain | `reasoning` + `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/support_contract.py`
- May edit: `packages/evaluation/tests/test_support_contract*.py`
- May edit: `scenarios/alex-v1/ground_truth/support_contracts.yaml` (additive fields only)
- May edit: `docs/architecture/eval-stubs/support_contract.v0.json`
- May edit: `docs/reports/alex-v1-truth-checklist.md`
- Must not edit: `scenarios/alex-v1/timeline/**`, `packages/attention/**`, plan files

## Hard depends

- R01 (support contract loader + alex-v1 truth baseline)

## Unlocks / enhances

- Fireworks Live Gate benchmark runs with human-inspectable arc checklist
- R04 support fitness scoring (resolution events + surface windows)

## Non-goals

- Timeline edits
- Runtime attention behaviour changes
- Scoring implementation (R04)

## Acceptance criteria

- [x] `valid_from` / `valid_until` alias `attention.window` in schema + loader
- [x] `resolution_event` timeline event id per resolvable arc
- [x] `expected_surface_window` human-readable per arc
- [x] `CONTEXT_ONLY` behaviour for dentist post-cancel arc
- [x] `docs/reports/alex-v1-truth-checklist.md` — one row per arc
- [x] Tests for new fields and alias validation

## Test plan

- `uv run pytest packages/evaluation/tests/test_support_contract.py`
- `uv run ruff check packages/evaluation`

## Privacy constraints

- Support contracts remain evaluator-only ([ADR-011](../../docs/adr/011-observable-support-challenges-only.md))
