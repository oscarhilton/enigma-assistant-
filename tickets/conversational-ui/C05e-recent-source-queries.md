# C05e — Recent source queries (email, WhatsApp quote)

**Status:** landed  
**May edit:** `apps/api/src/personal_enigma/api/demo_chat.py`, `apps/api/src/personal_enigma/api/demo_tools.py`, `apps/api/src/personal_enigma/api/demo_orchestrator.py`, `apps/api/src/personal_enigma/api/routes/demo.py`, `apps/api/src/personal_enigma/api/conversation_context.py`, `apps/api/tests/test_c05e_source_quote.py`, `packages/privacy/src/personal_enigma/privacy/egress/disclosure.py`, `apps/web/src/enigma/**`

## Goal

Answer provenance-style questions about recent sources without treating chat history as truth, and without sending wholesale raw mail or chat to a remote model.

Example utterances:

- "What's the latest from my emails?"
- "Did Elena say whether her parents are definitely coming?"
- "What exactly did she say?"

## Hard invariants (WhatsApp / source quotes)

These are product theses, not polish. Named here so C05e, C12, and SEC-06 share one vocabulary — not a new ADR.

1. **CHAT ≠ WORLD** — raw chat is evidence only, never the world model. Derived facts and open obligations come from structured extraction (`apply_chat_messages`), not from replaying the thread.
2. **QUOTE ≠ REMOTE CONTEXT** — verbatim source text may render locally (`source.quote`, kind `source_quote`, `local_only`) without entering Fireworks. `recent_dialogue` projected for egress may know a quote was shown (`summary`); it must not carry the body.
3. **EXPIRY ≠ LOSS OF ALL UTILITY** — raw quote can disappear (SEC-06 7-day `RAW_TTL`) while independently justified derived state survives (`Elena confirmed her parents are coming Saturday.`).

## Constraints

- Resolve from world state / fixture evidence, not transcript LLM guess
- Conservative when evidence is missing ("I don't know.")
- No wholesale Notes, raw mail, or raw chat bodies to remote models
- `source.quote` wire result is a handle (`quoted_locally`, `source_id`); verbatim body is a local turn item
- Expired raw (SEC-06 TTL) cannot be quoted; derived facts may remain
- `whatsapp.search` / `whatsapp.send` sit on `DENIED_REMOTE_CAPABILITIES` next to Gmail wholesale tools
- Follow-up turns after a local quote must not replay the body through `remote_context_sent`, compacted tool results, or `project_recent_dialogue_for_egress`

**Soft depends:** C05d
