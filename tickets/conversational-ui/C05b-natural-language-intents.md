# C05b — Natural-language intent resolution + availability query

**Status:** done  
**Branch:** `ticket/C05b-natural-language-intents`  
**May edit:** `apps/api/src/personal_enigma/api/demo_intents.py`, `intent_router.py`, `demo_availability.py`, demo route wiring, API tests

**Hard depends:** C05  
**Soft depends:** C00 (checkpoint calendar evidence)

## Problem

C05 canonical phrase handlers work; natural-language variants fail with "I'm not sure I follow."

Architecture (frozen):

```
language flexibility → small typed intent → deterministic Enigma capability
```

No LLM for intent routing.

## Deliverables

- [x] `normalize_utterance` strips case, punctuation, apostrophes, whitespace, trailing `/`
- [x] `resolve_intent()` maps phrase **families** to typed `ConversationIntent` kinds
- [x] `build_intent_turn` dispatches via `resolve_intent()` → existing `build_*_turn` handlers
- [x] New `availability_query` capability answers from checkpoint world state (calendar evidence)
- [x] Jan 19: "Am I free this weekend?" mentions Saturday brunch obligation / `cal-brunch-parents`
- [x] NL variants: "What's urgent?", "What's next?", "What do I need to do now?" work like canonical intents
- [x] Greeting family unchanged; unknown stays unknown (no command incantation list)
- [x] API tests cover phrase families + Jan 19 availability factuality
- [x] Do **not** change AttentionState contract, policy weights, C07 assist lifecycle

## Out of scope

- Free-form LLM agent routing
- Restaurant recommendations ("Where should I book brunch?")
- Reopening architecture / ADRs
