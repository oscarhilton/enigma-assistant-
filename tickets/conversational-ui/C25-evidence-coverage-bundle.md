# C25 — Evidence coverage bundle + courier / Goose projection

**Status:** in_progress (Phase A/B landed locally)  
**Branch:** `ticket/C25-evidence-coverage-bundle`  
**Domain:** conversational-ui  
**May edit:** `apps/api/src/personal_enigma/api/evidence_bundle.py` (new), `apps/api/src/personal_enigma/api/context_compilation.py` (mission / scope / catch_up), `apps/api/src/personal_enigma/api/conversation_context.py` (`catch_up` kind), `apps/api/src/personal_enigma/api/demo_orchestrator.py` (attach bundle), `apps/api/src/personal_enigma/api/respond_grounding.py` (coverage fence), `apps/api/tests/test_c25_*.py`, `apps/web/src/enigma/courier.ts`, `apps/web/src/enigma/EvidenceCourier.tsx`, `apps/web/src/enigma/ConversationViewport.tsx`, `apps/web/src/enigma/types.ts`, `apps/web/src/styles.css`, `packages/evaluation/scripts/alex_jan17_coverage_regression.script.yaml`, `packages/evaluation/fixtures/forensic/**`, `packages/evaluation/src/personal_enigma/evaluation/life_scripts/**`, `docs/adr/034-*.md`, `docs/architecture/conversational-stream.md`, `docs/architecture/conversational-ui.md`, `tickets/conversational-ui/**`

**Must not edit:** `ConversationCapsule` object shape (ADR-030 frozen) · `intent_router.py` · C16/C17 ledger · new product capabilities (`weather.*`, `news.*`)

**Hard depends:** [C20](./C20-capability-contract-on-wire.md) `capability_contract` on wire · [C14](./C14-conversation-activity-stream.md) activity projection  
**Soft (~):** [C21](./C21-grounded-values-no-invented-facts.md) · [C24](./C24-read-only-evidence-worker.md) (worker consumes bundle shape later)

**Architecture:** [ADR-034](../../docs/adr/034-evidence-coverage-bundle.md) · [ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md)

## Goal

**Coverage map first, character second.** Every read turn exposes what was searched, what was empty, what was unavailable, and whether Enigma may conclude the question is answered. The courier is the product face of that satchel — not a second mind. Product Language may later render it as THE Goose, but only as a projection.

Forensic specimen: 14-turn Jan 17 session (`alex_jan17_coverage_regression`).

## Frozen rules

1. `EvidenceBundle` is derived from compiler + tool trace — never model self-report.
2. `coverage_adequate == false` forbids “nothing needs you” and news/weather fiction.
3. The courier never speaks; Enigma narrates bundle-aware copy.
4. Fetch ≠ act: courier does not animate `assist.executing`.
5. `empty_pawed` ≠ permission to improvise ([C21](./C21-grounded-values-no-invented-facts.md)).
6. If rendered as THE Goose, presentation must not drive truth, tool choice, retries, work scheduling, escalation, or interruption.

## Deliverables

### Phase A — Bundle + compiler

- [x] `EvidenceBundle` / `FetchMission` types + `build_evidence_bundle()`
- [x] `catch_up` request kind + mission planned tools
- [x] Scope flip (`personal` / `work`), brunch referent → `subject_details`
- [x] `next_work` before `support_explain` for “what should I be doing?”
- [x] Attach `evidence_bundle` on `llm_trace`
- [x] Coverage-aware respond fence
- [x] `test_c25_evidence_bundle.py` + life script

### Phase B — Courier UI

- [x] `courier.ts` + `EvidenceCourier.tsx` (replaces ActivityStrip when bundle present)
- [x] Tests + styles

### Phase C — SSE (C14 follow-on)

- [ ] Live `fetching` state from activity stream

## Definition of done

Turns from the 14-turn dump produce honest bundles: calendar-only fetches mark `coverage_adequate: false`; weather/news mark `blocked`; brunch referent compiles `subject_details`. UI shows courier line in thread. C24 ticket updated to consume bundle shape.
