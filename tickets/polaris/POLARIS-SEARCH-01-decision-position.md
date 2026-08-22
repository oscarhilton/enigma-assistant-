# POLARIS-SEARCH-01 — DecisionPosition

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/POLARIS-SEARCH-01-decision-position` |
| Domain | `polaris` |

## Package boundary (hard)

- May edit: `packages/domain/**` (`DecisionPosition` + related typed snapshots), tests under that package, this ticket
- May read: Context Graph / world / attention / obligation projections; [polaris-search.md](../../docs/architecture/polaris-search.md)
- Must not edit: `packages/attention` ranking; Assist execution; `apps/web/**`; `scenarios/alex-v1/timeline/**`

## Hard depends

- [NORTHSTAR-SEARCH-DOCS](../northstar/NORTHSTAR-SEARCH-DOCS.md) `done`

## Soft depends (~)

- M20 NextAction schemas (reuse enums where honest)
- Historical grounded assertions (ADR-035 file not on `main`) — provenance ids if present, else evidence handles already in domain

## Unlocks / enhances

- POLARIS-SEARCH-02 / 03; ALEX-EVAL-01

## Non-goals

- Move generation, search, UI, global life score
- Dumping vault / mail / Notes into the position
- Personality or diagnostic fields ([ADR-011](../../docs/adr/011-observable-support-challenges-only.md))

## Acceptance criteria

- [ ] Typed `DecisionPosition` is a **minimum sufficient** snapshot of decision-relevant Context Graph (clock, open loops, blockers, availability/conflicts, attention qualification, resource/energy suitability, authority facts, provenance refs, assumptions)
- [ ] Same compiled inputs → stable key (transposition-ready); clock injection via existing `Clock` ([ADR-006](../../docs/adr/006-clock-injection.md))
- [ ] Excludes `PrivatePerson`, wholesale Notes, raw MIME, chat CoT, evaluator labels
- [ ] Unit table: Jan 15 dentist/critique overlap fixture compiles two overlapping calendar intervals + no manufactured obligation from standup existence
- [ ] Docs: package README pointer to [ADR-045](../../docs/adr/045-decision-position-moves-legality.md)

## Exit conditions

Done when tests prove compilation stability + exclusions, and 02/03 can import the type without reaching into vault internals.

## Test plan

- Fixture graph → position round-trip
- Negative: Notes body / person email must not appear on the position
- Clock change → different key; identical graph+clock → same key

## Privacy constraints

- Select-first: only decision-relevant fields
- Demo/Alex fixtures only until later Private tickets; no Oscar inbox
