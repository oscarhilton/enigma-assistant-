PHASE 2.5 — EXIT REPORT

Commit: 7230129
Scenario: alex-v1
Profile: canonical
Corpus fingerprint: bf89eb02c631669e
Provider: stub
Prompt versions: attention_assessment=v0

Critical recall: 1.000 [PASS] (threshold ≥ 0.95)
Recall delta: 0.000 [PASS] (threshold ≤ 0.01 (1 pp))
Background false alert: 0.000 / 1k [PASS] (threshold ≤ 1.0 / 1k)
Quiet-day attention: empty [PASS] (threshold must be empty (0 obligations))
Known privacy leaks: 0 [PASS] (threshold = 0)

Canonical Recall@K: 0.400 [PASS] (threshold measured (stub obs; no cliff))
Retrieval Precision@K: 0.667 [PASS] (threshold measured (stub obs))
Remote calls/1k: 0.000 [PASS] (threshold known stub (prefer local triage))
Cost/month: $0.0400 [PASS] (threshold known stub)
5k curve behaviour: linear_latency_flat_recall [PASS] (threshold no cliff / cost_blowup on CI ladder shape)

PHASE 2.5: PASS

---

Generated: 2026-08-16T17:11:17.418511+00:00
Notes:
- Canonical ~5k profile is documented; CI ladder uses finepersonas-mini expand-to.
- Remote calls / cost are stub measurements (provider=stub) for Demo Mode closeout.
- Storyline A/B uses identical critical surfaces (critical_displacement=0).
