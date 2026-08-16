# N01 — NextAction scorer stub

| Field | Value |
| --- | --- |
| Status | `todo` |
| Branch | `ticket/N01-next-action-scorer` |
| Domain | `next-action` |

## Package boundary (hard)

- May edit: `packages/attention/**` (or a dedicated next-action package if introduced by ADR), tests under that package
- May read: `packages/domain` (`NextAction`, enums)
- Must not edit: `AttentionItem` shape to absorb optional suggestions; `apps/web/**`; Shadow silence evaluation docs

## Hard depends

- M20

## Soft depends (~)

- M06 (existing attention heuristics for candidate pools)
- D18 (Demo can keep fixture stubs until scorer lands)

## Unlocks / enhances

- Soft-unlocks N02 cycling order; N03 preference weights

## Non-goals

- Full capacity / energy model
- Remote LLM ranking required for v0 (local heuristics OK)
- Notification delivery
- Productivity-max objective

## Acceptance criteria

- [ ] Protocol or pure function: candidates + lightweight context → ranked `NextAction` list (top is primary suggestion)
- [ ] Score sketch implemented as multiplicative fitness: usefulness × actionability × contextual fit × capacity × time fit × novelty/repetition penalty
- [ ] Urgency factor applied only when `urgency` is not none/absent
- [ ] REST / NOTHING candidates remain eligible when critical open loops are clear
- [ ] Does not emit walk/junk tidy-ups as `AttentionItem`
- [ ] Unit tests with a fixed context table (walk wins over high-effort deep work under high load / short free window)

## Test plan

- Deterministic fixture context → expected top category
- Urgency absent ⇒ urgency term does not reorder purely-optional candidates

## Privacy constraints

- Scorer stays local; no raw PrivatePerson / wholesale Notes to hosted models
