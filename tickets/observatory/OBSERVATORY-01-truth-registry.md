# OBSERVATORY-01 — Programme truth registry

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/OBSERVATORY-01-truth-registry` |
| Domain | `observatory` |

## Package boundary (hard)

- May edit: registry module (prefer `packages/evaluation` or a thin `packages/observatory` **if this ticket introduces it with an architecture pointer**), `docs/architecture/observatory.md`, `docs/architecture/eval-stubs/capability_status.v0.json` (additive), tests, this ticket
- Must not edit: `apps/web` UI (that is 02); probe runners (03); PolarIS search; Council copy; Cortex; Assist; `scenarios/alex-v1/timeline/**`

## Hard depends

- RECON-05A–D closed on `main` (vault / retention / recall / worker scheduling — current tranche)

## Soft depends (~)

- Ticket Status fields and exit-condition checklists as **inputs**, never as sufficient `VERIFIED` evidence
- [milestone-map.md](../../docs/architecture/milestone-map.md) capability list (read-only)

## Unlocks / enhances

- OBSERVATORY-02

## Intent

A **machine-readable** registry that can distinguish, per capability:

`SPECIFIED` / `IMPLEMENTED` / `WIRED` / `VERIFIED` / `RUNNING` / `USABLE`

with evidence refs and dependency state ([observatory.md](../../docs/architecture/observatory.md)). Headline status is **derived**. `RUNNING` / `USABLE` may be recorded as `held: false` until [OBSERVATORY-03](./OBSERVATORY-03-runtime-probes.md).

## Non-goals

- UI
- Runtime probes
- Stored `percent_complete` / progress bars as source of truth
- New Council members or star-named types
- Claiming PolarIS / Life Scripts / C28 inside this ticket

## Acceptance criteria

- [ ] Registry loads capability records conforming to [capability_status.v0.json](../../docs/architecture/eval-stubs/capability_status.v0.json)
- [ ] Each rung is `{ held, evidence_refs[] }`; `held: true` with empty refs **fails** validation
- [ ] No `percent_complete` / `progress` field is accepted (`additionalProperties: false`)
- [ ] Headline status = highest rung whose evidence is sufficient **and** whose hard deps are not demoting
- [ ] Seed at least: calendar READ, Assist PREPARE, Next Action stub, Goose courier, PolarIS search, Harbour readiness (docs-only → `SPECIFIED` at most)
- [ ] Headline rungs remain distinguishable as implemented / wired / runtime-verified (`VERIFIED`+`RUNNING`) / user-usable — no second enum
- [ ] Exit test: forging `USABLE.held=true` without probe/user-path refs is rejected
- [ ] Exit test: a capability whose hard dep is not `VERIFIED` cannot headline `USABLE`
- [ ] Docs remain the constitution; this ticket does not rewrite [council.md](../../docs/architecture/council.md)

## Exit conditions

Done when 02 can render from the registry **without** a human typing a completion percentage, and CI rejects fake `held: true` rungs.

## Test plan

- Schema validate seed records
- Negative: `percent_complete` key rejected
- Negative: `USABLE.held=true` + empty `evidence_refs` rejected
- Derivation table: fixture graph of 3 capabilities with one broken hard dep

## Privacy constraints

- Registry holds ticket/test/probe ids, not `PrivatePerson`, Notes, or raw mail
- Demo/Alex fixtures only until later Private tickets
