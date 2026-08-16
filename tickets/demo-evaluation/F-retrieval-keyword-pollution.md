# Feature scenario — retrieval-keyword-pollution

| Field | Value |
| --- | --- |
| Status | `done` |
| Domain | `demo-evaluation` |
| Related | D07, D08c, M14 |
| Branch | `ticket/f-quality-attacks` |
| Path | `scenarios/feature/retrieval-keyword-pollution/` |

## Intent

Many background messages share canonical keywords (e.g. “review”); retrieval must still prefer Atlas/canonical evidence.

## Package boundary

- `scenarios/feature/retrieval-keyword-pollution/**`
- `packages/evaluation/.../metrics/retrieval.py` (`canonical_evidence_recall_at_k`)
- `packages/evaluation/tests/test_f_quality_attacks.py`

## Acceptance

- [x] Canonical evidence recall@K measured under keyword pollution (mini fixture)
- [x] Atlas evidence appears in top-K despite many background “review” messages
- [x] Mini fixture sufficient for PR CI (no HF download)
