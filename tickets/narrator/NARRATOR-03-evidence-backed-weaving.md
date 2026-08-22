# NARRATOR-03 — Evidence-backed weaving and receipts

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/NARRATOR-03-evidence-backed-weaving` |
| Domain | `narrator` / `demo-evaluation` |

## Package boundary (hard)

- May edit: weaving / receipt projection over `NarrativeBeat`, evaluator YAML under evaluation/`ground_truth` (not timeline), tests, docs pointers, this ticket
- Must not edit: PolarIS searcher; Harbour types (read only); C12 frozen speech rules; Observatory visual language; `scenarios/alex-v1/timeline/**`

## Hard depends

- [NARRATOR-02](./NARRATOR-02-handoff-narrative-beats.md) `done`
- [RECON-08](../recon/RECON-08-alex-eval-catalogue.md) `done` (`alex-music-readiness` exists)

## Soft depends (~)

- [HARBOUR-01](../harbour/HARBOUR-01-activity-readiness-model.md) / [HARBOUR-02](../harbour/HARBOUR-02-minimum-viable-start.md) (readiness facts)
- [POLARIS-SEARCH-01](../polaris/POLARIS-SEARCH-01-decision-position.md) (bearing consumes a position)
- [OBSERVATORY-02](../observatory/OBSERVATORY-02-observatory-ui.md) (map mythic jot → structured event)
- [ALEX-EVAL-01](../demo-evaluation/ALEX-EVAL-01-life-positions.md) — cite, do not fork Alex

## Unlocks / enhances

- Honest mythic framing in ordinary chat; Observatory receipts; Life Script `response_meaning` stays public-effect

## Intent

Factual-clause grounding, visible uncertainty, expandable receipts, mythic vs engineering projection, and Alex eval cases.

A whimsical jot cannot outrun evidence. Unknowns stay unknown. Irrelevant Titans stay silent. A multi-layer music-readiness turn may weave Goose → Harbour → relevant specialist(s) → PolarIS into **one or two short jots**, then ordinary chat. The user can react mid-conversation. Engineering/Observatory maps the jot to the hop + evidence **without CoT**.

## Non-goals

- Auto-COMMIT because the story felt complete
- Profiling via “favourite mythic method”
- Forcing every cast member into the music turn
- Replacing C12 Life Scripts

## Acceptance criteria

- [ ] Eval: whimsical `line` that mentions an unreferenced meeting/location/update **fails**
- [ ] Eval: `ableton_update_state` remains `unknown` through Goose + Harbour + PolarIS jots ([RECON-08](../recon/RECON-08-alex-eval-catalogue.md) `alex-music-readiness`)
- [ ] Eval: unattested Titan/factor produces no beat (`suppress`)
- [ ] Eval: music turn beat sequence includes fetch (Goose) → readiness (Harbour) → only relevant lens/titan → bearing (PolarIS); concise (≤2 NORMAL jots unless CURIOUS)
- [ ] Eval: user utterance after a beat is accepted as a normal turn (no narrator-mode flag required)
- [ ] Observatory/FORENSIC: mythic_frame stripped; `event` + `evidence_refs` remain; no deliberation field
- [ ] PolarIS vs Harbour split survives the story (ready ≠ should now)
- [ ] Intention preserved on PolarIS defer (same as Harbour/RECON-08)

## Exit conditions

Done when the music weave passes the negatives above, and Observatory can click a jot to the underlying hop without a CoT pane.

## Test plan

- Grounding table: each clause → fact_ref or fail
- Music fixture weave + user mid-turn reply
- Negative: invent Ableton-updated; invent “session with Jordan”; speak `recovery` Titan with no fatigue evidence
- Receipt expand: NORMAL jot → FORENSIC hop list

## Privacy constraints

- Evaluator-only fixtures; never LLM prompt corpus
- Demo never shares Private roots ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))
