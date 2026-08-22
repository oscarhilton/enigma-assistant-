# BRAIN-03 — Live recalculation and stale-branch invalidation

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/BRAIN-03-live-recalculation` |
| Domain | `conversational-ui` |

## Package boundary (hard)

- May edit: search invalidation wiring (stimulus → recompute), Lens stale styling, tests
- Must not edit: Assist execution; retention policy; Cortex as writer

## Hard depends

- [BRAIN-02](./BRAIN-02-pv-explorer.md) `done`

## Soft depends (~)

- POLARIS-SEARCH-05 transposition invalidation
- Event Spine / attestation / clock steps (use whatever landed; do not restore C28 in this ticket)

## Unlocks / enhances

- Honest Lens during 06/07; user trust that old lines die

## Non-goals

- Background search as a personality
- Keeping a fossil PV after evidence dies (C39 Fossil Test)

## Acceptance criteria

- [ ] Evidence/state change (clock jump, attestation, receipt, blocker cleared, calendar cancel) **recomputes** the branch tree
- [ ] Stale branches are **visibly invalid** in Lens (label + not selectable as current)
- [ ] New PV does not silently inherit ply-0 from the stale tree
- [ ] Example: dentist cancel event `w2-cal-dentist-cancel` → overlap line invalid; `after_cancel: do_not_renag` holds
- [ ] No COMMIT as a side effect of recalculation

## Exit conditions

Done when a scripted clock/world-event test shows stale UI + fresh search, and 07 can rely on invalidation.

## Test plan

- Fixture: overlap position → cancel dentist → trace `invalidated_by` includes cancel id
- UI: stale class present; current PV replaced
- Negative: recalculation does not call `assist.approve`

## Privacy constraints

- Invalidation uses evidence ids already in the graph
- Do not re-fetch wholesale sources “just in case”
