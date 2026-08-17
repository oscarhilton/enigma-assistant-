# C05c — Relative availability + conservative typo tolerance

**Status:** done  
**Branch:** (local)  
**May edit:** `apps/api/src/personal_enigma/api/intent_router.py`, `demo_availability.py`, API tests

**Hard depends:** C05b  
**Soft depends:** C00 (checkpoint calendar evidence)

## Problem

C05b handles weekend / Friday night / Saturday availability. Users also ask about nearer horizons ("later?", "this afternoon", "tomorrow") and occasionally typo "free" as "fee".

## Deliverables

- [x] New `availability_query` periods: `later_today`, `this_afternoon`, `this_evening`, `tomorrow`
- [x] Deterministic bounds from injected checkpoint `at` (SimulationClock), never wall clock
- [x] Contextual typo repair: `fee` → `free` in availability-shaped phrases only (`intent_router`)
- [x] Conservative answers from checkpoint calendar evidence — no overclaiming free time
- [x] Jan 19 acceptance tests for all utterances + negative cases ("What is the fee?", "Feel free to do it")
- [x] Do **not** change AttentionState contract, policy weights, C07 assist

## Out of scope

- Recurrence, NLP framework, LLM routing
- "Next Tuesday after lunch", general spellchecker
- Global message rewriting
