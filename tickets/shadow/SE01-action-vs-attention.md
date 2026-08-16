# SE01 — User action vs attention log

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/SE01-action-vs-attention` |
| Domain | `shadow` |
| Baseline | [shadow-evaluation.md](../../docs/architecture/shadow-evaluation.md) (Q1, Q2, Q5, Q6 joins) |

## Package boundary (hard)

- May edit: `packages/evaluation/**` (or thin `packages/shadow_eval/**` if created) for action / candidate schemas + join helpers
- May edit: `apps/api/**` / `apps/worker/**` only for append-only local writers of the stub schemas
- May edit: tests + fixtures under the same packages
- Must not edit: `packages/simulation/**/environment.py` / `EnvironmentMode` (S01)
- Must not edit: Demo scenario corpora, Demo ground-truth semantics, full product UI

## Hard depends

- None for schema stubs / docs alignment
- Implementation of live writers: S01 soft-landed (Shadow root exists)

## Soft depends (~)

- S01 Shadow scaffold (mode + storage identity)
- S03 Shadow attention log (candidate stream to join against)
- SE02 (shared subject refs with suppress audit)

## Unlocks / enhances

- Q1 act-on recognition, Q2 nearly-forgot, Q5 memory Δ, Q6 timing distributions
- Feed for [SE03](./SE03-weekly-shadow-review.md)

## Non-goals

- Full UI for labelling actions
- OS accessibility / keylogging — only explicit in-app or connector-derived actions
- Remote telemetry of action streams
- Changing attention ranking (M06)

## Acceptance criteria

- [ ] Documented stub schemas `shadow.user_action/v0` and join against `shadow.attention_candidate/v0` (see architecture doc)
- [ ] Typed models or JSON-schema fixtures validating both shapes
- [ ] Join helper stub: given actions + candidates → per-subject match records (empty OK)
- [ ] Tests: schema round-trip; join does not read Demo ground truth
- [ ] Privacy: no raw attendee emails / Notes bodies required in the action schema

## Test plan

- Fixture: one acted mail with prior candidate → join hit
- Fixture: acted item with no candidate → novel-miss candidate for Q7
- Assert Demo eval packages still import cleanly

## Privacy constraints

- Local Shadow root only
- Prefer domain ids over provider payloads in persisted actions
