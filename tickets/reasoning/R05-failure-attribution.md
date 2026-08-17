# R05 — Failure attribution

| Field | Value |
| --- | --- |
| Status | `done` |
| Branch | `ticket/R05-failure-attribution` |
| Domain | `demo-evaluation` |

## Package boundary (hard)

- May edit: `packages/evaluation/src/personal_enigma/evaluation/failure_attribution.py` (create)
- May edit: `packages/evaluation/tests/test_failure_attribution.py`
- May edit: `packages/evaluation/src/personal_enigma/evaluation/report.py` (failures.json enrichment)
- Must not edit: `packages/attention/**`, `packages/reasoning/**` transport, `scenarios/alex-v1/timeline/**`

## Hard depends

- [R03](./R03-llm-judge.md) (A/B arm outputs)
- [R04](./R04-support-fitness.md) (per-checkpoint scoring)

## Soft depends (~)

- None

## Unlocks / enhances

- [R07](./R07-reasoning-value-gate-report.md) diagnostic narrative per disagreement
- Actionable regression templates (e.g. parents/brunch miss)

## Non-goals

- Auto-fixing attributed failures during the gate sprint
- Shadow Mode behavioural attribution (future)
- Changing ingestion or attention policy based on attribution (report-only)

## Acceptance criteria

- [ ] For every Arm A vs Arm B disagreement at a checkpoint, classify root cause:
  `INGESTION` · `IDENTITY` · `RETRIEVAL` · `MEMORY` · `INTERPRETATION` · `ATTENTION_POLICY` · `NEXT_ACTION_POLICY` · `TIMING`
- [ ] Decision tree: candidate existed? → evidence correct? → LLM caught heuristic miss? → policy vs timing
- [ ] `failures.json` enriched with attribution codes + per-case narrative
- [ ] Parents/brunch regression template documented as exemplar failure case
- [ ] Attribution runs on both attention and next_action disagreements independently

## Test plan

- Synthetic disagreement fixtures → expected attribution bucket
- Brunch miss scenario → `INGESTION` or `RETRIEVAL` (when candidate missing) vs `INTERPRETATION` (when LLM catches heuristic miss)
- Agreement cases → no spurious attribution entries

## Privacy constraints

- Attribution narratives reference obligation ids and evidence ids only — no PrivatePerson or raw mail bodies in exported JSON
- Demo Mode artefacts only

## Notes

- Architecture: [reasoning-value-gate.md](../../docs/demo/reasoning-value-gate.md) (decision tree)
