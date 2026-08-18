# C09b — Discourse focus vs objects in the response

**Status:** specified (Life Script green on C09 deterministic path; live UI findings unmet)  
**Branch:** implement on `ticket/C09-llm-conversational-boundary` (C09 owns `conversation_context.py`)  
**May edit (when implementing):** `apps/api/src/personal_enigma/api/conversation_context.py`, `apps/api/src/personal_enigma/api/demo_orchestrator.py`, `apps/api/src/personal_enigma/api/demo_assist.py`, `apps/api/src/personal_enigma/api/routes/demo.py`, C09 tests  
**Must not edit:** `intent_router.py` phrase families · C09 tool registry (no new tools) · a polish LLM · `"help!"` as a router phrase

**Hard depends:** [C09](./C09-llm-conversational-boundary.md) harness  
**Soft (~):** C09 live Fireworks proof  
**Contract:** [C12](./C12-life-scripts.md) `packages/evaluation/scripts/alex_jan19_focus_vs_radar.script.yaml`  
**Architecture:** [conversational-ui.md — discourse focus](../../docs/architecture/conversational-ui.md#discourse-focus--objects-in-the-response)

C12 documents this slice and holds the Life Script. It does **not** implement focus in C09 production files.

## Forensic findings (Demo UI · Jan 19 10:00 · 2026-08-17)

Session was entirely `PATH=intent_router`, `REMOTE CONTEXT SENT=none`. Trace made this visible.

1. 🔴 **UI still on intent_router, not real C09.** C09 is not speaking in this session.
2. 🟠 **Conversation focus is changed by secondary rendered objects.** Radar brunch stole TOKEN.
3. 🟠 **Explicit / named referent recovery needs the LLM path.** `"draft colour"` / `"token inventory"` are not regex.
4. 🟠 **Asynchronous Assist completion is not attributed to its originating action.** Delayed brunch “Done” after `"help!"` looked like a reply to the current turn.

Do **not** add `"help!"` / `"heeeelllppp!!"` to the router. Leave that inability as evidence the router must die.

## Product boundary

```
objects_in_response[]  ≠  conversation_focus
```

Merely rendering “also on radar: brunch” must **not** steal focus from TOKEN.

```
ConversationContext
├─ current_subject_id
├─ current_subject_kind
└─ focus_reason
```

`focus_reason` is C09-owned. Do not silently teach the router English.

| Transition | Focus |
| --- | --- |
| USER explicitly selects an item | change |
| MODEL answers primarily about an item | may change |
| HORIZON MODIFIER (`this week?`) | preserve unless the response clearly replaces it |
| SECONDARY CARD RENDERED | **do not** change |
| FAILED / UNKNOWN TURN | **do not** change |

Natural sequence the Life Script freezes:

- `"What is urgent right now?"` → focus = TOKEN (`item-obligation_token_audit`)
- `"this week?"` → horizon; brunch may be secondary; focus stays TOKEN
- `"what about the week after?"` → horizon again; focus stays TOKEN
- `"What is the draft colour?"` → lexical recovery to TOKEN (C09)
- `"Can you help me do that?"` → Assist TOKEN. BRUNCH here is the bug.
- `"I need help with the token inventory"` → named referent → Assist TOKEN
- `"I need help with the design tokens"` with brunch injected as focus → Assist TOKEN, not brunch
- `"help!"` / `"heeeelllppp!!"` → social, no Assist
- Delayed `"Done — Saturday brunch is booked"` → parent correlation on the original Assist; must not appear as a reply to the current user turn; update the Assist card, not conversational prose

## Work (C09, not C12)

- [ ] **(a)** `focus_reason` on `ConversationContext`. Preserve focus across horizon modifiers and secondary radar cards. `update_context_from_turn_items` must not treat every `attention_item` as a subject change. Life Script `preserve_subject` / `secondary_items_may_include` is the regression.
- [ ] **(b)** Assist completion attributed via parent correlation. Delayed verified results update the originating Assist card. `must_not · appear_as_reply_to_current_user_turn`. Today this is **deferred** on the Life Script (`event: assist_verified`) — missing product surface, like `assist.explain`.
- [ ] **(c)** C09 still not speaking in the forensic UI session. Path must be the real planner (`llm` / `fireworks`), not a debug string claiming C09 while `intent_router` ran and remote context was none.

## Out of scope

- Expanding `intent_router` phrase families (including `"help!"`)
- New C09 tools
- A second polish LLM
- Web UI Life Script player ([C12](./C12-life-scripts.md) next UI work)
