# D14 — Live Demo attention (alex-v1 pipeline)

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/D14-live-demo-attention` |
| Domain | `demo-ui` |

## Package boundary (hard)

- May edit: `apps/api/src/personal_enigma/api/routes/demo*.py`, `apps/api/tests/test_demo*.py`, `apps/api/pyproject.toml` (add obligations dep if needed)
- May edit: `apps/web/src/demo/**` (prefer API; demote/remove Atlas fixture fallback for attention)
- May edit: `tickets/demo-ui/D14-*.md`, `tickets/README.md`, `docs/architecture/milestone-map.md`
- Must not edit: scenario corpus (`scenarios/**`), real ingestion sources, privacy transforms, Shadow Mode paths

## Hard depends

- D05 (SimulationEngine / timeline)
- D08 (alex-v1 canonical life)
- D10 (Demo UI `/demo/*` chrome)

## Soft depends (~)

- D08c (background profile merge on `SyntheticMailSource.for_scenario`)
- D13 (Why / Attention payload shape)

## Unlocks / enhances

- Product demos show scenario-derived attention instead of hardcoded Atlas/Maya stubs
- Interactive timeline ↔ obligations/attention path without CLI eval

## Non-goals

- Full D08e canonical-scale (~5k) loads in the interactive UI
- Shadow Mode / Private Mode attention
- Reopening MVP architecture or inventing a corpus “D08f”
- Replacing memory browser stubs (separate ticket)

## Acceptance criteria

- [x] On demo start / timeline day or step / reset: load canonical alex-v1 (± configured background profile) through synthetic sources → merge/obligations → `HeuristicAttentionEngine` (remote reasoning off)
- [x] Replace `_STUB_ATTENTION_BASE` with live `AttentionItem`-derived payloads on `/demo/attention`
- [x] `/demo/why/<id>` uses evidence narratives from merged obligations where possible
- [x] Web prefers API; offline/fixture path does not resurrect Atlas/Maya attention stubs when the API is the source of truth
- [x] DEMO banner + `DemoEnvironment` invariants preserved (no real Gmail/Apple)
- [x] API tests assert attention titles come from scenario-derived data (not hardcoded Atlas strings); demo mode still required

## Test plan

- `uv run pytest apps/api/tests/test_demo.py`
- Smoke: `ENIGMA_ENVIRONMENT_MODE=demo` → step timeline a few hours → GET `/demo/attention` shows Maya/Q1 titles; advance day changes the set; reset restores epoch
- Confirm no real connector credentials are read
- Web: start Vite **without** absolute `VITE_API_BASE` (use `/demo` proxy); Pause then Next event still advances; 10× auto-plays; Attention refreshes with the clock

## Privacy constraints

- Never attach ground-truth `signal_class` / evaluator labels to attention payloads
- Keep remote LLM disabled by default for demo attention ranking
- Demo storage remains under Demo roots only ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))

## Pragmatic performance note

Background corpus rebuild is cached per session reset. Attention is recomputed on start, day, step, and reset from synthetic sources filtered by the D02 `SimulationClock` (`until=now`). Interactive UI uses the `demo` background profile (small), not D08e canonical scale. Full `SimulationEngine` checkpoint I/O stays on the eval/CLI path so clicks stay light.
