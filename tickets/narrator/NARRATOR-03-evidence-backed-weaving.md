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

Factual-clause grounding, visible uncertainty, expandable receipts, mythic vs engineering projection, Alex eval cases, and a selective daily-fable rendering that tells the **shape of the day** without sounding like the underlying schema.

A whimsical jot cannot outrun evidence. Unknowns stay unknown. Irrelevant Titans stay silent. A multi-layer music-readiness turn may weave Goose → Harbour → relevant specialist(s) → PolarIS into **one or two short jots**, then ordinary chat. The user can react mid-conversation. Engineering/Observatory maps the jot to the hop + evidence **without CoT**.

For daily fables, the trace is evidence but not a prose template. Select meaningful change; preserve mundane specificity; omit aggressively; keep the mythology legible without lore. Dryness is preferred to whimsy. Wit may be cutting toward machinery, bureaucracy, procedures, or the cast's self-importance, but remains affectionate toward the user.

## Non-goals

- Auto-COMMIT because the story felt complete
- Profiling via “favourite mythic method”
- Forcing every cast member into the music turn or daily fable
- Replacing C12 Life Scripts
- Turning every event into a sentence
- A productivity score, moral, triumph arc, diagnosis, or invented emotional interpretation
- Divine/theological framing of the celestial cast

## Acceptance criteria

- [ ] Eval: whimsical `line` that mentions an unreferenced meeting/location/update **fails**
- [ ] Eval: `ableton_update_state` remains `unknown` through Goose + Harbour + PolarIS jots ([RECON-08](../recon/RECON-08-alex-eval-catalogue.md) `alex-music-readiness`)
- [ ] Eval: unattested Titan/factor produces no beat (`suppress`)
- [ ] Eval: music turn beat sequence includes fetch (Goose) → readiness (Harbour) → only relevant lens/titan → bearing (PolarIS); concise (≤2 NORMAL jots unless CURIOUS)
- [ ] Eval: user utterance after a beat is accepted as a normal turn (no narrator-mode flag required)
- [ ] Observatory/FORENSIC: mythic_frame stripped; `event` + `evidence_refs` remain; no deliberation field
- [ ] PolarIS vs Harbour split survives the story (ready ≠ should now)
- [ ] Intention preserved on PolarIS defer (same as Harbour/RECON-08)
- [ ] Daily-fable eval uses canonical Alex evidence without editing `timeline/**`; an ordinary day remains understandable to a reader who knows nothing about Enigma's cast
- [ ] Daily-fable output selects roughly 2–4 meaningful beats rather than covering every available event
- [ ] Daily-fable output may use 0–2 earned mythic cameos by default; any named cameo maps to a structured event beneath it
- [ ] Copy eval rejects “the gods” / deity framing and accepts restrained celestial collective language where grounded (“the constellation”, “the sky”, etc.)
- [ ] Copy eval rejects unsupported motive/emotion language (`distracted`, `anxious`, `procrastinating`, `lazy`, etc.) unless evidence explicitly supports it
- [ ] Copy eval rejects a fable whose humour makes the user the principal punchline
- [ ] Copy eval rejects synthetic one-event-per-sentence cadence even when each sentence is individually grounded
- [ ] Copy eval accepts omission and an unresolved ending when that is the honest shape of the day

## Canonical Alex daily-fable fixture

Use **Wednesday 14 January 2026** from canonical Alex v0.2.1 as an initial tone/grounding fixture because it contains a small, legible shape without requiring invented Enigma intervention:

- prior evidence: checkout decision remained unresolved on 13 January;
- 14 January: Tom proposes climbing Sunday at The Castle;
- the climbing event is placed at 10:00 Sunday;
- 16:40: Alex sends Maya the recommendation to park checkout behind tokens and revisit mid-Q2 with research;
- 16:45: checkout reminder is completed.

The evaluator should permit a dry, selective account such as “one question became a decision; one Sunday acquired a climbing wall” **only when every factual element remains recoverable from the fixture**. It must not claim Alex was distracted, rescued, anxious, procrastinating, or advised by PolarIS/Mole/Goose unless future structured interaction events actually establish those facts.

This fixture tests the central distinction:

- **today's canonical timeline can support a restrained fable about the day;**
- **future Enigma traces may earn additional cast cameos;**
- the Narrator must never silently substitute the richer fictional version for the evidence actually present.

## Exit conditions

Done when the music weave passes the negatives above, the Alex daily-fable fixture passes grounding + tone selection tests, and Observatory can click a jot to the underlying hop without a CoT pane.

## Test plan

- Grounding table: each clause → fact_ref or fail
- Music fixture weave + user mid-turn reply
- Alex 2026-01-14 daily-fable selection + style eval
- Negative: invent Ableton-updated; invent “session with Jordan”; speak `recovery` Titan with no fatigue evidence
- Negative: label Alex distracted/anxious/procrastinating without evidence
- Negative: full-cast roll call; deity language; one-event-per-sentence trace dump; user-as-punchline
- Receipt expand: NORMAL jot → FORENSIC hop list
- Plain-English recoverability: strip mythic proper nouns and verify the underlying account still makes sense

## Privacy constraints

- Evaluator-only fixtures; never LLM prompt corpus
- Demo never shares Private roots ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md))
