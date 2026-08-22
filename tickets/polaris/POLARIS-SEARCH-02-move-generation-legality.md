# POLARIS-SEARCH-02 — Move generation + legality

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/POLARIS-SEARCH-02-move-generation-legality` |
| Domain | `polaris` |

## Package boundary (hard)

- May edit: Foundry-facing capability → candidate move adapter (likely `packages/domain` move types + a dedicated module under `packages/attention` or successor `packages/polaris` **if introduced by this ticket with an ADR pointer**), tests
- Must not edit: Assist approve/execute paths; LLM tool registry authority; `AttentionItem` shape; web UI

## Hard depends

- [POLARIS-SEARCH-01](./POLARIS-SEARCH-01-decision-position.md) `done`

## Soft depends (~)

- ADR-024 recipes (procedure as future move generator — must not implement a recipe engine here)
- N01 candidate pool (read-only)

## Unlocks / enhances

- POLARIS-SEARCH-04

## Non-goals

- Ranking / search / Lens
- New authority rungs
- Semantic model as legality oracle

## Acceptance criteria

- [ ] Capabilities emit **candidate moves** (typed, bounded, predicted local effects)
- [ ] Legality filter: authority + consent + resources + constraints ([ADR-045](../../docs/adr/045-decision-position-moves-legality.md))
- [ ] Illegal moves are **excluded**, not low-scored
- [ ] READ / PREVIEW / PREPARE / COMMIT mapped; ply-0 COMMIT still requires Assist
- [ ] Example: dentist/critique overlap — `start_deep_work_through_both_events` illegal or poor-and-excluded; `resolve_calendar_conflict` / `prepare_cancel_dentist` legal at PREPARE ceiling
- [ ] Semantic proposals, if any, cannot mark an illegal move legal

## Exit conditions

Done when a deterministic fixture table lists candidates vs legal set, and 04 can search **only** the legal set.

## Test plan

- Authority ceiling: SUPPORT position cannot emit COMMIT moves
- Resource: 5-minute window cannot list 90-minute deep work as legal
- Consent: outbound notify without grant is illegal

## Privacy constraints

- Moves carry capability ids + local effect sketches, not raw third-party dossiers
- Default deny ([ADR-015](../../docs/adr/015-capability-scoped-disclosure-not-data-access.md))
