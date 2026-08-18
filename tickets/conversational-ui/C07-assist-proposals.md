# C07 — Assist proposal UI (stub execution)

**Status:** done  
**Branch:** `ticket/C07-assist-proposals`  
**May edit:** `apps/web/src/enigma/items/Assist*.tsx`, demo assist endpoints

## Deliverables

- [x] Basic approve endpoint + result in conversation
- [x] `AssistProposalView` with structured approve flow for brunch scenario
- [x] "Can you help me do that?" → structured `assist_proposal` (never auto-execute)
- [x] Explicit approval → synthetic execute → verify → `assist_result`
- [x] Session overlay (`completed_item_ids`) after verified brunch assist; frozen Jan 19/20 snapshots unchanged

**Follow-on:** [C07b](./C07b-assist-completed-not-task-completed.md) — ASSIST COMPLETED ≠ TASK COMPLETED. Brunch overlay is SATISFIES; TOKEN draft is ADVANCES.

**Hard depends:** C04, C02
