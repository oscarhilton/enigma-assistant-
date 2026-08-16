# Phase 2.5 — Exit report + noise metrics closeout

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/eval-noise-metrics` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/**` (noise metrics wiring, Phase 2.5 exit artefact writer)
- May edit: `docs/reports/phase-2.5-exit-report.md` (+ companion `.json`)
- May edit: `docs/architecture/milestone-map.md` (fold in missing D13 row)
- May edit: `tickets/demo-evaluation/D07-evaluation-runner.md` amendment checklist
- Must not: implement D14, Shadow Mode, or FinePersonas 115k downloads

## Hard depends

- D07, D08c–e
- F-correctness wave + quality attacks + import-boundary gates on `main` (for overall PASS)

## Soft depends (~)

- D08c gate hardening artefacts

## Acceptance criteria

- [x] Background suppression rate / false alerts per 1k / compression in `enigma-eval` `metrics.json`
- [x] Storyline recall under noise (A/B) wireable via `--spine-metrics` / `spine_metrics`
- [x] Remote reasoning rate stub + cost per simulated month stub in report JSON
- [x] Mini-fixture tests
- [x] Immutable `docs/reports/phase-2.5-exit-report.md` after F-* gates land
- [x] D13 row on milestone map
- [ ] Annotated tag command for `v0.2.0-demo` prepared; tag only if report is PASS

## Test plan

- [x] `uv run pytest packages/evaluation/tests/test_phase25_exit.py packages/evaluation/tests/test_runner.py`
- [x] Regenerated exit report on tip of `main` after F-* merges

## Privacy constraints

- Demo Mode only; no Private roots or HMAC material in reports
