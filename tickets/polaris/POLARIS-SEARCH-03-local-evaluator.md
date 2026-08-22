# POLARIS-SEARCH-03 — Local evaluator

| Field | Value |
| --- | --- |
| Status | `future` |
| Branch | `ticket/POLARIS-SEARCH-03-local-evaluator` |
| Domain | `polaris` |

## Package boundary (hard)

- May edit: local evaluation module (same package home as 02/04 once chosen), tests, docs pointers
- Must not edit: interruption policy as a value head; person records; UI; Assist

## Hard depends

- [POLARIS-SEARCH-01](./POLARIS-SEARCH-01-decision-position.md) `done`

## Soft depends (~)

- N01 fitness sketch (usefulness × actionability × fit × capacity × time × novelty) — reuse ideas, do not delete N01
- [ADR-011](../../docs/adr/011-observable-support-challenges-only.md) challenge vocabulary (evaluator-only)

## Unlocks / enhances

- POLARIS-SEARCH-04

## Non-goals

- Universal life score / centipawn-of-life
- Personality profiling
- Replacing Attention qualification
- Productivity-max objective

## Acceptance criteria

- [ ] Evaluator scores **local successor positions** for this user/now ([ADR-046](../../docs/adr/046-local-evaluation-under-uncertainty.md))
- [ ] No single global life score field on user or world
- [ ] Factors may include urgency, consequence, effort, switching cost, momentum, energy suitability, uncertainty reduction, reversibility, optionality, blockers released, social consequence — all evidence-linked
- [ ] Urgency multiplies only when urgency exists (ADR-010 parity)
- [ ] REST / NOTHING / wait remain eligible
- [ ] Policy/prior separate from value: tests show an illegal move never “wins” by score
- [ ] Uncertainty × consequence exposed as a **search-effort hint** (consumed by 04)
- [ ] Example: `december-expenses` — gather-receipts beats DO-EXPENSES-NOW under admin-friction + short window (invariant, not exact scalar)

## Exit conditions

Done when 04 can ask “how does this successor look?” without a global objective, and tests lock the no-life-score invariant.

## Test plan

- Factor table on Alex fixtures (expenses, brunch, token blocker)
- Negative: adding a `life_score` field to the person record fails lint/test
- REST wins over high-effort deep work under high load / short free window (N01 parity)

## Privacy constraints

- Energy suitability is situational, not a diagnosis
- No remote raw rejects with PII; eval stays local
