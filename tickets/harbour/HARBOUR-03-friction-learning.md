# HARBOUR-03 — Friction learning / environment improvement

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/HARBOUR-03-friction-learning` |
| Domain | `harbour` |

## Package boundary (hard)

- May edit: advisory environment-improvement proposals over **explicit** repeated blocker evidence, tests, docs pointers, this ticket
- Must not edit: PolarIS search; retention policy; Assist COMMIT; profiling stores; Observatory UI chrome

## Hard depends

- [HARBOUR-02](./HARBOUR-02-minimum-viable-start.md) `done`

## Soft depends (~)

- Event spine / execution receipts ([RECON-06](../recon/RECON-06-event-action-spine.md)) as evidence of repeated fetch-the-cable
- [ADR-011](../../docs/adr/011-observable-support-challenges-only.md) — observable friction only
- [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md) — no home-layout biography

## Unlocks / enhances

- Honest “keep the cable with the keyboard” advice; later PolarIS may treat lower transition cost as a fact **after** the user accepts

## Intent

Detect **repeated** setup blockers from explicit evidence and **propose** environment changes (e.g. keep the power cable with the keyboard). Advisory only. No profiling, no hidden optimisation, no rearranging the house.

## Non-goals

- Auto-applying environment changes
- Inferring personality, ADHD flags, or “how Alex is”
- A second searcher that starts routing the day around setup
- Tyranny: nagging until the cable moves

## Acceptance criteria

- [ ] Two+ evidenced same-blocker episodes can mint a PREPARE-level proposal (“put cable in the cupboard with the keyboard”)
- [ ] One episode is not enough (no one-shot nag)
- [ ] Proposal is rejectable; rejection does not raise urgency
- [ ] No silent rewrite of readiness facts when the user ignores the proposal
- [ ] Observatory can show the proposal as evidence, not as CoT

## Exit conditions

Done when a fixture of repeated music-setup fetches produces one advisory proposal and **zero** autonomous world edits.

## Test plan

- Two evidenced cable-fetches → one proposal
- One fetch → no proposal
- Negative: ignored proposal must not become a PolarIS “must do now”

## Privacy constraints

- Store blocker codes + counts + last clock, not a furniture map
- User-forgettable; Demo/Alex first
