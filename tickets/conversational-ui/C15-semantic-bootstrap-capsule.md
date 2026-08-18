# C15 — ADR-029 handoff (frustration after unsatisfied private request)

**Status:** in_progress (AC met on primary checkout; **not** in PR [#92](https://github.com/oscarhilton/enigma-assistant-/pull/92))  
**Branch:** `ticket/C15-semantic-bootstrap-capsule`  
**Domain:** conversational-ui  
**May edit:** `apps/api/src/personal_enigma/api/context_compilation.py` (ADR-029 handoff recovery — **not** `intent_router` phrase families, **not** `"anything coming up?"` catalogues), `apps/api/src/personal_enigma/api/semantic_bootstrap.py`, `apps/api/tests/test_c15_*.py`, `docs/adr/029-*.md` (handoff note), `docs/adr/031-*.md` (cross-link only), `tickets/conversational-ui/**`  
**Must not own / must not edit:** [C09c](./C09c-conversation-capsule.md) capsule object, reducer, TTL, `conversation_context.py` inherit-before-interpret. **C09c stays frozen. Do not reopen.** Bootstrap must not copy capsule `previous_authority` as a grant.  
**Must not edit:** `intent_router.py` phrase families · D08f corpus · a polish LLM · C14 activity-strip presentation · timers / decomposition / action-claim policing / external evidence / source-importance ranking

**Hard depends:** [C09](./C09-llm-conversational-boundary.md) compiler / ADR-029 independent axes  
**Soft (~):** C09c capsule retention (landed · **frozen**) — this ticket consumes retained context; it does not amend the capsule  
**Architecture:** [ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md) · [ADR-030](../../docs/adr/030-conversation-capsule.md) (frozen) · [ADR-031](../../docs/adr/031-semantic-bootstrap-compiler-grants-context.md)

## This slice (live-model falsification)

C15 is a live-model falsification at the **ADR-029 handoff**, not “conversation continuity and action integrity.”

Context retention is fine (C09c). The subsequent contract failed to use retained context.

**Flagship: the `"ffs"` turn.** Preceding six dialogue turns present, token-audit subject preserved, unresolved request (inspect mail / what matters) recoverable — yet compiled `CONVERSATION` / `CONVERSATION_ONLY` / `NONE`, so no private tools; Fireworks ranks emails from transcript residue.

### Narrow assertion

Given frustration following an unsatisfied private-world request:

1. Recover the unresolved request semantically.
2. Compile a fresh `PRIVATE_QUERY` with `READ` authority.
3. Expose and require an appropriate private-world tool.
4. Use transcript only to recover intent and scope.
5. Never treat transcript content as fresh ranking evidence.

Proof does **not** require good importance ranking. If the source tool cannot establish importance, honest limitation after re-grounding is correct. Ranking quality is a later excluded contract.

Do **not** fold into C15: timers, decomposition, action-claim policing, external evidence, source-importance ranking.

## Compiler rule

Frustration / `"ffs"` / similar after an unsatisfied `PRIVATE_WORLD` request must not compile `CONVERSATION_ONLY` with zero tools. Recover the prior private request → `PRIVATE_WORLD` + `READ` + candidate families (attention / agenda / source as appropriate). Scan *user* recent_dialogue and retained `unresolved_request` — never assistant ranking residue.

Handoff = recover unsatisfied private request into profile+families, **not** re-classify frustration as phatic.

## Semantic bootstrap (already landed)

ADR-031 bootstrap remains: the model interprets language; the compiler grants context. Do not teach `interpret_request` `"anything coming up?"`.

- [x] ADR-031 + FixtureSemanticBootstrap + conservative merge
- [x] Tests in `apps/api/tests/test_c15_semantic_bootstrap.py`
- [x] Life Script `packages/evaluation/scripts/alex_jan19_semantic_bootstrap.script.yaml`

## Deliverables (this handoff)

- [x] Frustration after unsatisfied private request compiles `PRIVATE_QUERY` / `READ` / non-empty private tools
- [x] Resolved private subject + attribute request compiles `PRIVATE_QUERY` / `READ` / `subject_details` / explain+source tools
- [x] Six prior dialogue turns + `"ffs"` unit test (`test_c15_adr029_handoff.py`)
- [x] Transcript is not ranking evidence (`must_not` in that test)
- [x] ADR-029 handoff note
- [x] C09c files untouched
- [ ] Land compiler handoff + `test_c15_adr029_handoff.py` on a C15 (or coordinated C09 follow-up) PR — **not** in `enigma-wt-C09-llm-conversational-boundary` today; do not split dirty primary files into that worktree

## Out of scope

- Reopening C09c / amending `ConversationCapsule`
- Expanding `intent_router` English catalogues
- Source-importance ranking quality
- Timers, decompose, capability-promise policing, `EXTERNAL_WORLD`
- Teaching the compiler `"anything coming up?"`
