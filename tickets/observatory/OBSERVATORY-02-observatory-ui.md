# OBSERVATORY-02 — Enigma Observatory UI

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/OBSERVATORY-02-observatory-ui` |
| Domain | `observatory` |

## Package boundary (hard)

- May edit: `apps/web` **engineering** Observatory route (not HomePage, not Cortex 3D, not Lens), client types, tests, docs pointers
- Must not edit: Assist approve handlers; conversation chrome as a talking sky; PolarIS search; `BRAIN-*` UI; Council product names on the always-visible layer

## Hard depends

- [OBSERVATORY-01](./OBSERVATORY-01-truth-registry.md) `done`

## Soft depends (~)

- C10 Cortex panel patterns (read-only layout only)
- C06 provenance debug (evidence chips)

## Unlocks / enhances

- RECON-06 (visible missing-spine edges); OBSERVATORY-03 (later live rungs)

## Intent

An **engineering-facing** UI over the truth registry that visibly answers:

what exists · what is wired · what is tested · what is running · what is user-usable · what is missing · **why**

Include:

- System / constellation **wiring graph** with missing and broken edges drawn as gaps (not decorative stars)
- Capability detail with **receipts** (evidence refs)
- A clear **Can I use this now?** (`USABLE` or the demotion reason)
- Current sprint / progress as **counts of derived rungs**, never a typed-in percent
- Later hook for Alex benchmark integration ([RECON-08](../recon/RECON-08-alex-eval-catalogue.md) / ALEX-EVAL) — placeholder panel is enough
- Later hook for Harbour readiness evidence / blockers ([harbour.md](../../docs/architecture/harbour.md)) — ids and reason codes only, **no chain-of-thought**

Celestial visual language is **restrained and truthful**. Empty sky is honest.

## Non-goals

- Home-page Observatory; theatrical animation; “the Council is in session”
- New named Council members to fill graph nodes
- Click-to-COMMIT; operating Enigma from the graph
- Implementing PolarIS Lens
- Minting `RUNNING` / `USABLE` without 03 (show `held: false` + “awaiting probes”)

## Acceptance criteria

- [ ] Route is engineering/lab (Alex Lab or `/observatory`), **not** the conversational home
- [ ] Graph nodes = capabilities; edges = hard deps; missing/broken edges labelled with reason codes
- [ ] Detail pane: six rungs + evidence refs + last_verified + broken_wires; implemented / wired / runtime-verified / user-usable remain visibly distinct
- [ ] **Can I use this now?** is a boolean + reason, bound to derived `USABLE`
- [ ] Placeholder for Harbour `blockers[]` / unknowns (empty until HARBOUR-01); must not render deliberation text
- [ ] Sprint strip uses the programme order in [README.md](./README.md) (01→02→RECON-06…); progress = rung counts
- [ ] Copy tests: no “complete”, “feeling lucky”, or star-named Council aliases as node titles
- [ ] Frozen: inspect ≠ control plane

## Exit conditions

Done when a screenshot/test shows a seeded capability with a broken edge and an honest “not usable” answer, without a percent widget.

## Test plan

- Render seed registry: all six rungs visible
- Broken hard-dep fixture → child **Can I use this now?** is no
- Negative: no `percent` / `complete%` in UI copy tests

## Privacy constraints

- Engineering/Demo only
- Do not display raw Notes or attendee emails from evidence refs
