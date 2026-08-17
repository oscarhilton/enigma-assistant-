# C21 — Grounded values; no invented private-world facts

**Status:** todo  
**Branch:** `ticket/C21-grounded-values-no-invented-facts`  
**Domain:** conversational-ui  
**May edit:** `apps/api/src/personal_enigma/api/demo_orchestrator.py` (respond-phase grounding fence), `apps/api/src/personal_enigma/api/context_compilation.py` (examples/placeholders instruction on GENERAL_KNOWLEDGE / missing evidence only), `packages/evaluation/scripts/alex_jan19_week_grounding.script.yaml` (extend, do not replace), `packages/evaluation/scripts/alex_jan19_speech_acts.script.yaml` (venue invention flags), `packages/evaluation/src/personal_enigma/evaluation/life_scripts/**` (new `must_not` flags if needed), `packages/evaluation/tests/test_life_scripts.py`, `apps/api/tests/test_c21_*.py`, `docs/architecture/conversational-ui.md` (pointer), `tickets/conversational-ui/**`

**Must not edit:** `intent_router.py` · `ConversationCapsule` · C15 bootstrap · a new “facts” tool that dumps the private world · more assists · C09c

**Hard depends:** [C09](./C09-llm-conversational-boundary.md) ([ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md) lanes 2–4)  
**Soft (~):** [C20](./C20-capability-contract-on-wire.md) — missing external search must defer, not fake a table · [C12](./C12-life-scripts.md)

## Goal

**Before more assists.** Private-world values (colours, venues, addresses, who was chosen) come from retrieved evidence or are labelled as examples/placeholders. The model must not invent them.

Forensic dump: [`packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt`](../../packages/evaluation/fixtures/forensic/alex_jan19_continuity_integrity.dump.txt) ([C23](./C23-continuity-integrity-life-script.md)).

Exact lines:

- Turn 37: `go for it!` — dump invented Sunny Side Café / 123 Main St., Bistro Brunch / 456 Oak Ave., Garden Terrace / 789 Pine Rd.
- Turn 51: `ok lets go` — dump invented `color-primary` `#0066FF` and a token table as the inventory

This is mostly a **compiler/respond fence + Life Script**, not a new tool. Week grounding already fails no-tool invention from `referent_candidates`. Speech-acts already `must_not` invent external venues. This ticket closes the remaining hole: invented **private** details (token colours) and invented **external** tables when lane 4 has no search.

## Frozen rules

1. The model may possess general knowledge. It may not manufacture current-world evidence ([ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md) §10).
2. Specific private claims (the colours, the venue selected) require a tool result this turn or an honest “I don’t have that.”
3. Specific external claims (restaurants, addresses) require external evidence. Missing capability → defer, do not fake a table ([C20](./C20-capability-contract-on-wire.md)).
4. If the respond phase uses a hypothetical, it must be marked example/placeholder — never as Alex’s world.
5. Conversation state / `referent_candidates` / capsule / active_thread may bind “the colours” to TOKEN. They may not supply the hex values.

## Deliverables

- [ ] Respond fence / tests: unsourced colour values, venue names, addresses fail
- [ ] Life Script clauses in [C23](./C23-continuity-integrity-life-script.md) for dump turn 37 (`go for it!`) and turn 51 (`ok lets go`)
- [ ] `must_not` flags: `invent_private_world_value`, `invent_external_venue` (reuse if already named)
- [ ] No new C09 production tool whose job is “give the model more private biography”

## Out of scope

C15 live bootstrap falsification; C09c; adding web search; more assists; P2 essay/table style ([C22](./C22-adhd-response-shape.md)).

## Definition of done

C21 tests and Life Script clauses fail invented restaurants, addresses, and design-token colours unless those strings appear in this-turn tool evidence or are explicitly labelled examples. Gate: [C23](./C23-continuity-integrity-life-script.md).
