# C05 — Deterministic conversation intents

**Status:** done  
**Branch:** `ticket/C05-conversation-intents`  
**May edit:** `apps/web/src/enigma/**`, `POST /demo/conversation/message` in demo routes

## Deliverables

- [x] "What needs me?" → structured `attention_summary` turn
- [x] Combines context + next_actions in copy without collapsing buckets
- [x] Additional intents: "What can wait?", "What changed?", "What am I waiting on?", "What should I do next?"
- [x] Each intent answers from projected world state (never chat history) and then stops
- [x] API tests cover all four new intents on Jan 19 and Jan 20

**Hard depends:** C02, C04, C00
