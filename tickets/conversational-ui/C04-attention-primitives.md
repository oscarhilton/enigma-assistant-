# C04 — Attention primitives + presentation plan

**Status:** in_progress  
**Branch:** `ticket/C04-attention-primitives`  
**May edit:** `apps/web/src/enigma/items/**`

## Deliverables

- [x] `AttentionItemView` — badge from `item.bucket`: **NEEDS YOU / CONTEXT / CAN WAIT** (never WORTH DOING on attention items)
- [x] `AttentionSummaryView` — opening from `PresentationPlan.chat_opening_count`; WORTH DOING copy only from `next_actions[]`
- [x] **Silence:** `proactive_silence` → no conversation item; demo event log only
- [x] Combines `context[]` and `next_actions[]` in copy without collapsing buckets

**Hard depends:** C01, C02
