# M20 — NextAction domain schemas

| Field | Value |
| --- | --- |
| Status | `done` (this PR) |
| Branch | `docs/next-action-model` |
| Domain | `domain-model` |

## Package boundary (hard)

- May edit: `packages/domain/**`, this ticket, docs links in `docs/architecture/next-action.md` / ADR-010
- Must not edit: `packages/attention/**`, `apps/web/**`, Shadow silence docs

## Hard depends

- M01

## Soft depends (~)

- None

## Unlocks / enhances

- Soft-unlocks N01 scorer stub, D18 Demo Next Action chrome, N02–N03 preference loop

## Non-goals

- Ranking / scoring implementation (N01)
- Demo UI (D18)
- Preference persistence (N03)
- Changing `AttentionItem` fields

## Acceptance criteria

- [x] `ActionCategory`, `Effort`, `Urgency`, `ActionContext` enums in `packages/domain`
- [x] `NextAction` Pydantic model with title, reason, category, estimated_minutes, effort, context, source_ids, urgency, value, confidence, `optional=True`
- [x] Round-trip tests; exported from package `__init__`
- [x] Architecture + ADR document the three-level split

## Test plan

- Unit tests for enum values and `NextAction` `model_dump` / `model_validate`

## Privacy constraints

- Domain types are private-local; no remote DTOs; no PERSON_* on NextAction face fields
