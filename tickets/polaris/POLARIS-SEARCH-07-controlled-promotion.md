# POLARIS-SEARCH-07 — Controlled promotion

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/POLARIS-SEARCH-07-controlled-promotion` |
| Domain | `polaris` |

## Package boundary (hard)

- May edit: feature flag / planner selector for Next Action **output** in Alex Lab (later My Enigma only with explicit follow-on), tests, docs, this ticket
- Must not edit: Attention interrupt policy; Assist auto-execute; authority ladder; Hugging Face boot

## Hard depends

- [POLARIS-SEARCH-06](./POLARIS-SEARCH-06-shadow-mode.md) `done`

## Soft depends (~)

- BRAIN-02 / BRAIN-03 (operators can see stale lines)
- P02 Life Scripts still green with flag on (regression)

## Unlocks / enhances

- Polaris as the WORTH DOING planner in Alex Lab under flag

## Non-goals

- Default-on for My Enigma / Oscar
- Treating PV as a committed multi-step plan
- Replacing Attention silence semantics

## Acceptance criteria

- [ ] Promotion is **explicit** (flag / config), default off
- [ ] Gate: ALEX-EVAL-02 shows measurable improvement or non-regression on agreed invariants (document the bar in the PR; do not “feel better”)
- [ ] Gate: 06 shadow log reviewed for illegal-move leaks (zero)
- [ ] With flag on, user still sees **one** next action (or REST/NOTHING), never a twenty-step itinerary
- [ ] COMMIT still Assist; flag must not raise authority
- [ ] Flag off restores previous planner (06 parity tests reused)
- [ ] Life Scripts / P02: no new architecture-named utterances required for pass

## Exit conditions

Done when Alex Lab can enable Polaris ply-0 as NEXT **without** changing Assist/Attention authority, with published tournament + shadow evidence, and Oscar has not been opted in.

## Test plan

- Flag matrix: off = 06 baseline; on = search ply-0; Assist still propose→approve
- Invariant suite from ALEX-EVAL-01 must pass under on
- Negative: PV length > 1 must not appear in the user Next Action payload

## Privacy constraints

- Promotion evidence is Alex synthetic + shadow traces
- My Enigma remains off until a later ticket after SEC-05 / pilot ethics
