# SE11 — Open-loop due resolution

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE11-open-loop-due-resolution` |
| Domain | `shadow` (implements obligations/memory bridge) |
| Baseline | [open-loop-commitments.md](../../docs/architecture/open-loop-commitments.md) |

## Package boundary (hard)

- May edit: `packages/obligations/**` (preferred) and `packages/domain/**` only for commitment due fields
- May edit: focused tests under those packages
- May amend: `docs/architecture/open-loop-commitments.md`
- Must **not** edit: Demo attention UI (`apps/web/src/demo/**`), Gmail OAuth, `EnvironmentMode`
- Must **not** force attention surface merely because `due_resolved_at` is set

## Hard depends

- M16 commitment tracking (`done`)

## Soft depends (~)

- SE04 when open-loop candidates participate in suppress logging
- M15 merge evidence timestamps for resolver anchors

## Unlocks / enhances

- Deterministic due dates for open loops
- Orthogonal CONFIDENCE / STATUS / ATTENTION axes
- Clearer Memory UI freshness (“Last evidence” / “Last observed”)

## Non-goals

- Full Memory product redesign
- CRM / email send
- Interrupting the user on every open due

## Acceptance criteria

- [ ] Store human due phrase **and** resolved concrete due (nullable when uncertain)
- [ ] Deterministic resolver: e.g. observed Sat 14 Mar + `"before Friday"` → Fri 20 Mar (documented rule + tests)
- [ ] Schema/docs rename guidance: prefer **Last evidence** / **Last observed** over ambiguous “Last”
- [ ] Three axes documented in code comments or types: CONFIDENCE, STATUS (`OPEN`/`RESOLVED`/`CANCELLED`/`UNCERTAIN`), ATTENTION (`SURFACE`/`SUPPRESSED`/`DEFERRED`)
- [ ] Valid fixture: confidence=0.90, status=OPEN, attention=SUPPRESSED
- [ ] Memory/privacy note: UI may show real names; model/privacy view keeps USER / PROJECT_B tokens
- [ ] Attention policy remains responsible for *when* to surface; setting due does not auto-notify

## Test plan

- Resolver unit table for weekday phrases relative to anchor dates
- Ambiguous phrase → unresolved due + UNCERTAIN (or equivalent) without crash
- Attention independence: due present + SUPPRESSED does not call delivery adapter in stub

## Privacy constraints

- Commitment text local; remote summaries transformed
- No wholesale Notes to hosted models
