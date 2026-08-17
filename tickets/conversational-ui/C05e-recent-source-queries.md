# C05e — Recent source queries (email, etc.)

**Status:** todo  
**May edit:** TBD — `apps/api/src/personal_enigma/api/demo_intents.py`, `intent_router.py`, ingestion/fixture stubs as needed

## Goal

Answer provenance-style questions about recent sources without treating chat history as truth.

Example utterances (not in C05d):

- "What's the latest from my emails?"
- "Where did I leave my keys?" (object location — may split to separate ticket)

## Constraints

- Resolve from world state / fixture evidence, not transcript LLM guess
- Conservative when evidence is missing ("I don't know.")
- No wholesale Notes or raw mail to remote models

**Soft depends:** C05d
