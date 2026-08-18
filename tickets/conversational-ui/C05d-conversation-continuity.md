# C05d — Conversational continuity + compositional follow-ups

**Status:** done · **frozen** (horizon modifiers only — do not patch referent bugs here)  
**Branch:** (local)  
**May edit:** `apps/api/src/personal_enigma/api/conversation_context.py`, `demo_intents.py`, `intent_router.py`, `demo_availability.py`, `routes/demo.py`, `apps/api/tests/test_demo_conversation_context.py`

## Architectural rule

```
WORLD STATE = durable facts (AttentionState, calendar, mail)
CONVERSATION CONTEXT = temporary referents for dialogue ("it", "another", "that")
```

Conversation context may resolve references. It may **not** establish world facts.

**Conversation may modify the query; it may not modify the truth.**

- Conversation context **MAY** carry forward intent
- Conversation context **MAY** modify horizon
- Conversation context **MAY** preserve requested cardinality
- World state is **ALWAYS** queried again, **NEVER** inferred from the previous answer

Requested cardinality (e.g. "top 3") is a **presentation preference**. It is not permission to invent extra next actions.

## Fence (confirmed — stop here)

Once the three discourse modifiers below are green, **stop teaching the router English**. Do not add more phrase families. **Do not patch subject-referent bugs** (`"today's action"`, `"why do I need to do this?"`, `"that's a completely different task"`) — those belong in [C09](./C09-llm-conversational-boundary.md).

Only these follow-ups, as period/horizon modifiers on the last intent:

- `"this week?"`
- `"tomorrow?"`
- `"and after that?"`

Example: `"What is urgent right now?"` then `"this week?"` reuses `attention_query` with `horizon = this_week` and **re-queries world state** over that horizon — it does not extrapolate the prior turn.

## Split with C09

| Slice | Job |
| --- | --- |
| **C05–d** | Deterministic capability + regression scaffold — **horizon modifiers only** |
| **[C09](./C09-llm-conversational-boundary.md)** | Normal human conversation — **semantic referents** |

| C05d (frozen) | C09 |
| --- | --- |
| `"this week?"` | `"this"` / `"that"` / `"today's action"` |
| `"tomorrow?"` | `"something else"` / `"anything else?"` |
| `"and after that?"` | `"why do I need to do this?"` / `"next week?"` |
| | `"let's start it"` / `"can we start it?"` |
| | `"that's a completely different task"` (referent recovery) |

C09 resolves further discourse into typed tool args. C05d does not grow a regex empire to cover the rest of English.

## Deliverables

- [x] `ConversationContext` on `DemoSession` — updated when Enigma presents structured items
- [x] "What should I do right now?" → `next_action_query` alias
- [x] "Nah, I can't be bothered" → acknowledge + session suppress (no checkpoint mutation)
- [x] "Another task I can do?" → alternate next action not in suppressed set
- [x] "How much time would it take?" → duration from referent + fixture estimates
- [x] "Do I have time?" → duration + later-today availability composition
- [x] Acceptance script API tests (Jan 19 · 10:00)
- [x] Fenced horizon follow-ups only: `"this week?"`, `"tomorrow?"`, `"and after that?"` — carry last intent, change horizon, re-query world
- [x] Cardinality-aware `"top N"` presentation — one strong next action; radar stays radar
- [x] Tests: `"this week?"` after urgent; top 3 acknowledges count without inventing actions

**Hard depends:** C05, C05b, C05c

## Out of scope (deferred)

- Further discourse / phrase families beyond the three fenced modifiers → [C09](./C09-llm-conversational-boundary.md)
- Object location queries ("Where did I leave my keys?") → C05e+ / [C09](./C09-llm-conversational-boundary.md) benchmark (keys→don't know)
- Recent email source queries → [C05e](./C05e-recent-source-queries.md)
- Durable user traits from rejection
- Productivity coach tone

## Feeds C09

Conversation context and compositional follow-ups (`resolve_referent`, duration/time-fit composition) become **`context.resolve_referent`** and related tools under [C09](./C09-llm-conversational-boundary.md) — referents from tool outputs/session, not transcript invention ([ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md)).
