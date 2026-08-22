# BRAIN-02 — Lens principal-variation explorer

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/BRAIN-02-pv-explorer` |
| Domain | `conversational-ui` |

## Package boundary (hard)

- May edit: `apps/web` Alex Lab forensic panel for **Lens** (not HomePage Cortex 3D), client types, tests
- Must not edit: Assist approve handlers; Cortex write paths; v1 conversation chrome as a talking brain

## Hard depends

- [BRAIN-01](./BRAIN-01-structured-search-trace.md) `done`

## Soft depends (~)

- C10 Cortex panel patterns (read-only)
- C06 provenance debug
- ALEX-EVAL-01 fixtures for demo traces

## Unlocks / enhances

- BRAIN-03; operator inspection during 06

## Non-goals

- Product-copy “Brain View” as inner life
- Operating Enigma from the explorer (no COMMIT click)
- Three.js requirement

## Acceptance criteria

- [ ] Alex Lab explorer shows: current position, best line, alternatives, confidence **fading with depth**, structured Council assessments (specialist factor families), **which lenses materially changed ranking**, provenance, assumptions, invalidation triggers, coverage gaps
- [ ] Copy / docs: **Lens**; ticket id may stay BRAIN-02. Internal nickname “Brain View” still means this structured pane — never hidden CoT
- [ ] Explicit empty state: “structured search trace” — not “what Enigma is thinking”
- [ ] Selecting a branch **PREVIEW**s it (inspect); does not PREPARE/COMMIT
- [ ] Frozen C10 rule restated: observability ≠ control plane
- [ ] Example: dentist-critique PV visible with `resolve_calendar_conflict` on ply-0 and faded later plies
- [ ] Example: calendar-coverage-gap shows incomplete picture (Goose/courier copy allowed); Polaris must not display a hallucinated free afternoon

## Exit conditions

Done when a screenshot/test proves the explorer renders a golden trace with fading confidence and no CoT text.

## Test plan

- Render golden trace: PV + alternatives present
- Negative: no “thinking” / “felt” / “wondered” / “Aldebaran was tired” strings in UI copy tests
- Click branch → no mutation API called
- Ranking-changed-by chips render from golden token-fuel trace

## Privacy constraints

- Alex Lab / Demo only
- Do not display raw Notes or attendee emails from provenance
