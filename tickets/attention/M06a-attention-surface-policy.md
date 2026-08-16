# Attention surface policy (wind-tunnel fix)

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/attention-surface-policy` |
| Domain | `attention` |

## Package boundary (hard)

- May edit: `packages/attention/**`, `packages/obligations/**` (merge/surface only)
- May edit: `apps/api/src/personal_enigma/api/routes/demo_attention.py` (consume surface policy)
- May edit: `tickets/attention/**`, `tickets/demo-scenario/F-*.md`, `tickets/demo-evaluation/F-*.md`, `tickets/README.md`, `docs/architecture/attention-surface.md`, `docs/architecture/milestone-map.md`, `docs/architecture/demo-corpus.md`
- Must not edit: identity, real ingestion sources, unrelated open identity PRs

## Hard depends

- M06 (attention engine)

## Soft depends (~)

- D08d (noise layer patterns)
- D14 (live demo wiring — merged into this branch for verification)

## Non-goals

- Full MESSAGE_ORIGIN taxonomy (follow-up ticket)
- Reopening MVP architecture / inventing D08f
- Broad Demo UI redesign

## Acceptance criteria

- [x] Bare calendar existence does not emit AttentionItems / calendar-only obligations
- [x] Past calendar events resolve when `now` is injected
- [x] Machine / newsletter / package mail never become INFERRED_COMMITMENT
- [x] Social questions → PENDING_REPLY (P2), not commitment 0.55
- [x] Unrelated machine mail and distinct social plans do not mega-merge
- [x] Default surface filter: P≥4 (P3 with timing); P2 held back
- [x] Deadline why-now distinguishes APPROACHING / DUE_SOON / DUE_TODAY / OVERDUE / STALE
- [x] F-* unit fixtures + docs (`docs/architecture/attention-surface.md`)

## Test plan

- `uv run pytest packages/attention packages/obligations`
- `uv run pytest apps/api/tests/test_demo.py`
- Manual: Demo Mode alex-v1 → Attention near brunch/token due dates → expect ~2 surfaced items

## Privacy constraints

- Local heuristics only; no remote model ranking required
- Why evidence stays on Why view; card body stays short
