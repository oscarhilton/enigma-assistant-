# C07b — ASSIST COMPLETED ≠ TASK COMPLETED

**Status:** in_progress (AC met locally; not merged — rides C09 dirty primary / [#92](https://github.com/oscarhilton/enigma-assistant-/pull/92), do not split)  
**Branch:** implement in the current conversational-ui checkout (do not clobber C09b / C14)  
**May edit:** `apps/api/src/personal_enigma/api/demo_assist.py`, `apps/api/src/personal_enigma/api/demo_tools.py` (approve effect only), `apps/api/src/personal_enigma/api/conversation_context.py` (`reconcile_action_focus` only), `apps/api/src/personal_enigma/api/demo_intents.py` (empty next-action copy), `apps/api/src/personal_enigma/api/routes/demo.py` (approve overlay), `apps/api/tests/test_demo_projection.py`, `apps/api/tests/test_demo_conversation_context.py`, `packages/evaluation/scripts/alex_jan19_assist_lifecycle.script.yaml`, `packages/evaluation/src/personal_enigma/evaluation/life_scripts/**`, `packages/evaluation/tests/test_life_scripts.py`, `docs/architecture/conversational-ui.md`, `docs/architecture/next-action.md`, `docs/adr/010-next-action-not-attention.md`, `tickets/conversational-ui/**`

**Must not edit:** `intent_router.py` phrase families · streaming UI (C14) · `"help!"` as a router phrase · C09 tool registry (no new tools)

**Hard depends:** [C07](./C07-assist-proposals.md)  
**Soft (~):** [C09](./C09-llm-conversational-boundary.md) (tool for truth; this ticket is world semantics)

## Invariant

**ASSIST COMPLETED ≠ TASK COMPLETED.**

Only an Assist whose verified effect **SATISFIES** the obligation may RESOLVE it. A draft Assist ADVANCES TOKEN (stays OPEN / IN_PROGRESS, next action “Review the draft”).

| Effect | Meaning |
| --- | --- |
| SUPPORT_ONLY | Prepared something; obligation remains |
| ADVANCES | New obligation state; recalculate next action |
| SATISFIES | Verified effect completes obligation |
| UNRELATED | Side effect does not mutate target |

`current_subject_id` may survive completion. `current_next_action_id` must not point at a non-action.

**Absence of recommendation is not evidence of absence of worthwhile activity.** Empty `next_action_ids` ≠ “Nothing worth doing.”

## Live finding

After verified Assist “I recorded a synthetic draft for Draft colour + spacing token inventory”: TOKEN disappeared, `next_action.get` → `[]`, copy “Nothing worth doing right now.”, stale `current_next_action_id`. C09 did the right thing (tool for truth). The bug was Demo overlay treating every verified Assist as SATISFIES.

## Deliverables

- [x] Document the invariant (conversational-ui.md · next-action.md · ADR-010)
- [x] Draft Assist ADVANCES; brunch booking SATISFIES
- [x] Clear stale `current_next_action_id`; keep `current_subject_id`
- [x] Empty next-action copy does not claim nothing worth doing
- [x] Life Script `alex_jan19_assist_lifecycle`

**Hard depends:** C07
**Unlocks / enhances:** [C16](./C16-attested-completion-invalidates-next-action.md) (attested completion must *stay* out of next-action — complementary invariant)
