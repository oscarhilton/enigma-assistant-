# Conversational stream — show what Enigma is doing

**Status:** Specified ([C14](../../tickets/conversational-ui/C14-conversation-activity-stream.md) · [ADR-027](../adr/027-streaming-presentation-adapter.md))  
**Principle:** Enigma shouldn't tell you that it's thinking. It should quietly show you what it's actually doing.

Presentation is part of Enigma’s magic. The conversational surface is not a flat chat log and not a fake chain-of-thought. It is a **structured projection of real Core events** plus the prose Enigma actually wrote.

This page is the conversation **activity layer**. Cortex ([cortex-visualizer.md](./cortex-visualizer.md) · [C10](../../tickets/conversational-ui/C10-cortex-brain-visualizer.md)) is a different projection of overlapping feeds — forensic / 3D, not the in-thread activity UI.

## Authority (unchanged)

```
FastAPI / Enigma Core     truth, events, orchestration, policy, execution
Conversational LLM        understands and speaks (ADR-020)
apps/web                  presents; never invents cognition
```

Do **not** move the agent into Vercel AI SDK backend architecture (`streamText` route handlers, Next.js as the orchestrator, `useChat` as source of truth). The model is not Enigma. Streaming presentation must not reverse that.

## Two concurrent streams

A turn is two streams over one HTTP response (or two SSE channels with the same `correlation_id`):

| Stream | Contents | UI |
| --- | --- | --- |
| **Machine events** | Capability hops as they happen (`availability.checked`, `assist.proposed`, …) | Activity rows / Assist cards |
| **Human response** | Token deltas of **actual Enigma prose** | Prose part |

They are concurrent: an activity can complete while prose is still arriving. Do not wait for the whole turn to paint “Checked your calendar.”

C09’s orchestrator is request/response today. **Token streaming is a C09 follow-on**, not a C14 blocker. Until Fireworks (or the local planner) emits deltas, the UI may:

1. Project a completed `llm_trace.tool_results` into a collapsed activity strip (v0, this slice).
2. Paint prose in one shot from `enigma_message` / structured items.

Do not invent execution latency to make (1) look like streaming.

## Progressive disclosure, not theatre

| Phase | Glyph | Rule |
| --- | --- | --- |
| Started | ◌ | Shown the moment the Core event exists |
| Done | ✓ | Swap when the event completes |
| Minimum lifetime | hundreds of ms | Visual only — **do not delay Core**. If the hop finished in 8ms, hold the row at ◌ for a short floor, then ✓. Never sleep the tool. |

Forbidden copy: “Thinking carefully…”, “Let me reason about this…”, spinner-only “Thinking”. Those are fake CoT. If nothing has happened yet, show nothing (or the composer wait state) — not a lie.

## Three projections of the SAME event

One `EnigmaActivityEvent`. Three views. No parallel cognition log.

| Mode | Where | What the user sees |
| --- | --- | --- |
| **NORMAL** | Conversation thread | One human line: “Checking your calendar…” → “Checked your calendar.” |
| **CURIOUS** | Same thread, collapsed | “Checked N things” → expand to a ✓ list of the same labels |
| **FORENSIC** | Under-bonnet | Existing `TurnTracePanel` (`llm_trace`) + `EgressDisclosurePanel` + Cortex (C10, deferred 3D) |

| Event | NORMAL / CURIOUS | FORENSIC |
| --- | --- | --- |
| `availability.checked` | Checked your calendar | Tool hop + args + result |
| `attention.queried` | Checked what needs you | `attention.get_current` trace |
| `referent.resolved` | Matched this to the token inventory | `context.resolve_referent` / subject id |
| `world.explained` | Checked why this matters | `world.explain` result |
| `assist.proposed` | Prepared an action — **card**, not a theatre line | Proposal payload |
| `assist.approved` | Approved — **card** | Approval hop |
| `assist.executing` | Booking brunch… (or generic “Carrying that out”) — **card** | Execution start |
| `assist.verified` | Booked brunch (or verified ack) — **card** | Verified result |
| `egress.allowed` | **Hidden** | Disclosure / membrane / LLM trace only |

Assists are factual state cards: **PROPOSED → APPROVED → EXECUTING → VERIFIED**. Parent-correlation completion updates the originating card; it must not appear as a reply to the current user turn ([C09b](../../tickets/conversational-ui/C09b-discourse-focus.md)).

## Turns are structured parts

Not `string[]`. A turn is ordered parts:

```
user
activity*          (NORMAL line or CURIOUS collapse)
prose?             (token-streamed Enigma copy — never invented)
next-action*       (existing NextActionView)
assist*            (proposal / result cards)
collapsed_activity (CURIOUS summary of the same activity*)
forensic?          (under-bonnet only)
```

Silence still appends **no** conversation item ([conversational-ui.md](./conversational-ui.md)). Activity for a silent evaluation lives in the demo event log / Cortex, not the transcript.

## Reuse existing feeds

Project; do not invent a second log.

| Source (today) | Projects to |
| --- | --- |
| `LlmTrace.tool_results` / `model_tool_request` | Activity kinds (v0, completed turn) |
| `ConversationItem` (`assist_proposal`, `assist_result`, `next_action`, …) | Assist / next-action parts |
| `EnigmaEvent` | Session-level refresh (attention / conversation) |
| `EgressDisclosure` | `egress.allowed` — FORENSIC only |
| `BrainEvent` (C10) | Same audit feeds → Cortex regions |

`BrainEvent` stays Cortex-shaped (`attention_qualified`, `egress`, …). Conversation activity stays capability-shaped (`attention.queried`, `egress.allowed`). Same hops, different vocabulary.

Tool → kind map (canonical + honest extensions for tools already on C09):

| Tool / item | Activity kind | Label |
| --- | --- | --- |
| `availability.check`, `availability.time_fit` | `availability.checked` | Checked your calendar |
| `agenda.get` | `agenda.queried` | Checked your week |
| `attention.get_current` | `attention.queried` | Checked what needs you |
| `context.resolve_referent` | `referent.resolved` | Matched this to the token inventory |
| `world.explain`, `attention.explain_why` | `world.explained` | Checked why this matters |
| `world.get_changes` | `world.changes` | Checked what changed |
| `world.get_blockers` | `world.waiting` | Checked what you're waiting on |
| `next_action.get` | `next_action.queried` | Checked what's worth doing |
| `next_action.get_alternatives` | `next_action.alternatives` | Looked for something else |
| `next_action.reject` | `next_action.rejected` | Noted you'd rather not |
| `referent.get_duration` | `duration.checked` | Checked how long this takes |
| `assist.propose` / `assist_proposal` | `assist.proposed` | Prepared an action |
| `assist.approve` | `assist.approved` | Approved |
| execution start (stream) | `assist.executing` | Booking brunch… / Carrying that out |
| `assist_result` ok | `assist.verified` | Booked brunch / verified message |
| disclosure sent | `egress.allowed` | forensic only |
| `conversation.acknowledge` | — | No activity row (session ack, not a world check) |

## Frontend library path

**Chosen:** `@assistant-ui/react` on **Vite** (`apps/web`) as a **presentation adapter**. Do not rewrite the app to Next.js because the getting-started posts use Next.

| Layer | Choice | Why |
| --- | --- | --- |
| Shell | assistant-ui primitives (`Thread`, `Composer`, custom tool-call / data-part renderers) | Streaming, activity rows, Assist cards as custom renderers |
| Runtime (now) | `ExternalStoreRuntime` over existing `ConversationItem[]` | We already own message state in `EnigmaProvider` |
| Runtime (when Core streams) | `AssistantTransport` | Agent state worth surfacing; bidirectional commands (`add-message`, approve Assist) |
| Wire | **Enigma-native SSE** (machine + prose), adapted in the client | Do not make Vercel UI-message `data-*` parts the source of truth |
| Backend | FastAPI remains the agent | ADR-020 |

**Rejected as the product path:**

| Alternative | Why not |
| --- | --- |
| Next.js + AI SDK `streamText` as the agent | Moves orchestration out of Enigma |
| `useChat` + AI SDK data-stream protocol as canonical wire | Couples Core events to Vercel part types; FastAPI would impersonate a Vercel route |
| assistant-ui **requires** Next | False — `@assistant-ui/react` is a React library; Vite plugin exists for `"use generative"` (we do not need that split: tools execute in FastAPI) |
| Custom chat only, forever | We would reimplement streaming viewport, tool renderers, and composer a11y |
| Rip `ConversationViewport` in the spec PR | Half-migrated shell; v0 is types + activity strip from existing traces |

Install `@assistant-ui/react` in a later C14 slice when wrapping the viewport is clean. v0 must not add the dependency “for later.”

## SSE shape (C09 follow-on; do not block the UI spec)

Illustrative — not implemented in C14 v0:

```text
POST /demo/conversation/message/stream
Content-Type: text/event-stream

event: activity
data: {"kind":"availability.checked","phase":"started","label":"Checking your calendar…","correlation_id":"…"}

event: activity
data: {"kind":"availability.checked","phase":"done","label":"Checked your calendar","correlation_id":"…"}

event: prose
data: {"delta":"Saturday is free after 11.","correlation_id":"…"}

event: turn_complete
data: {"items":[…],"llm_trace":{…}}
```

Until that endpoint exists, `POST /demo/conversation/message` remains request/response. The client projects `llm_trace` → activity events.

## Related

- [conversational-ui.md](./conversational-ui.md) — world state is truth; structured items; silence
- [ADR-020](../adr/020-llm-conversational-boundary-not-truth.md) — model understands and speaks; Enigma knows and acts
- [ADR-027](../adr/027-streaming-presentation-adapter.md) — this presentation choice
- [cortex-visualizer.md](./cortex-visualizer.md) — FORENSIC / 3D projection; not the activity strip
- [ethics.md](./ethics.md) — Cortex/activity show system events, not thoughts
