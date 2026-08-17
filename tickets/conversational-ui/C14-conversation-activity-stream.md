# C14 — Conversation activity stream (presentation of real events)

**Status:** done (v0 merged [#90](https://github.com/oscarhilton/enigma-assistant-/pull/90) · `22949ba`)  
**Branch:** `ticket/C14-conversation-activity-stream`  
**Domain:** conversational-ui (presentation)  
**May edit:** `apps/web/src/enigma/**`, `apps/web/src/pages/HomePage.tsx`, `apps/web/src/styles.css`, `apps/web/package.json` (assistant-ui later slice only), `docs/architecture/conversational-ui.md`, `docs/architecture/conversational-stream.md`, `docs/architecture/cortex-visualizer.md`, `docs/adr/027-*.md`, `tickets/conversational-ui/**`  
**May edit later (SSE, not v0):** `apps/api/src/personal_enigma/api/routes/demo.py` stream endpoint only — do not rewrite the orchestrator here  
**Must not edit:** `intent_router.py` · C09 `demo_tools.py` / `demo_orchestrator.py` / `conversation_context.py` (sibling in-flight) · Life Script YAML · Cortex r3f · Vercel/Next rewrite

**Hard depends:** [C09](./C09-llm-conversational-boundary.md) stream/events — `llm_trace.tool_results` already on the turn payload (request/response is enough for v0)  
**Soft (~):** [C10](./C10-cortex-brain-visualizer.md) — same events, different projection (Cortex stays forensic/3D; this ticket is the in-thread activity layer). Do not wait on r3f or HomePage Cortex wiring.

## Product principle

> Enigma shouldn't tell you that it's thinking. It should quietly show you what it's actually doing.

Architecture: [conversational-stream.md](../../docs/architecture/conversational-stream.md) · [ADR-027](../../docs/adr/027-streaming-presentation-adapter.md)

## Library recommendation (decided)

| Question | Answer |
| --- | --- |
| Frontend library | **assistant-ui (`@assistant-ui/react`) on Vite** — adapter, not a new app |
| Next.js rewrite? | **No** |
| Vercel AI SDK as backend? | **No** — FastAPI remains the agent |
| Wire | Enigma-native dual stream (machine events + prose deltas); client adapts |
| Runtime now | `ExternalStoreRuntime` over existing `ConversationItem[]` when wrapping the shell |
| Runtime later | `AssistantTransport` when C09 streams agent snapshots (“state worth surfacing”) |
| AI SDK UI `data-*` parts | Rejected as canonical wire; optional later *adapter* only |
| Fireworks token SSE | **C09 follow-on** — do not block this ticket’s spec or v0 stub |

Do not install `@assistant-ui/react` until a slice wraps the viewport cleanly. v0 is spec + types + activity strip from existing traces.

## v0 (this slice)

- [x] Architecture doc + ADR-027
- [x] Ticket + programme README row
- [x] `EnigmaActivityEvent` types + tool → kind → label map (`apps/web/src/enigma/activity.ts`)
- [x] Collapsed “Checked N things” strip projected from `llm_trace` on the completed turn (no SSE)
- [x] Did **not** rip `ConversationViewport` for assistant-ui in v0

## Later slices (same ticket or follow-on)

- [ ] Dual SSE from FastAPI (`activity` + `prose` events, same `correlation_id`)
- [ ] C09 orchestrator streams Fireworks tokens + tool hops (C09-owned)
- [ ] Progressive ◌ → ✓ with a short **visual** minimum lifetime (do not delay Core)
- [ ] assistant-ui primitives wrap viewport + composer; custom renderers for activity + Assist cards
- [ ] Assist cards: PROPOSED → APPROVED → EXECUTING → VERIFIED (parent-correlation completion)
- [ ] `AssistantTransport` once Core streams snapshots

## Event vocabulary (human labels)

Use these. `egress.allowed` is under-bonnet only.

| Kind | NORMAL / CURIOUS |
| --- | --- |
| `availability.checked` | Checked your calendar |
| `attention.queried` | Checked what needs you |
| `referent.resolved` | Matched this to the token inventory |
| `world.explained` | Checked why this matters |
| `world.attested` | Noted a change you told me |
| `assist.proposed` | Prepared an action (card) |
| `assist.approved` | Approved (card) |
| `assist.executing` | Booking brunch… / Carrying that out (card) |
| `assist.verified` | Booked brunch / verified ack (card) |
| `egress.allowed` | forensic only |

Honest extensions for tools already on C09 (`next_action.get`, `agenda.get`, …) live in the same map — see [conversational-stream.md](../../docs/architecture/conversational-stream.md). Do not invent hops that Core did not perform.

## Three projections

| Mode | UI today |
| --- | --- |
| NORMAL | Activity strip one-liner |
| CURIOUS | Collapsed “Checked N things” (same events) |
| FORENSIC | `TurnTracePanel` + `EgressDisclosurePanel` + Cortex (C10) |

## Out of scope

- Fake thinking text
- Expanding `intent_router`
- Polish LLM
- Cortex react-three-fiber
- Moving the backend to Vercel / Next
- Implementing Fireworks token stream in this slice
- Rewriting C09/C12 life scripts, `demo_tools`, `conversation_context`, or ADR-020 grounding

## Test plan

- Unit: tool name → activity kind + label; `egress.allowed` omitted from NORMAL/CURIOUS
- Unit: 1 hop → one-liner; N hops → “Checked N things”
- Viewport: strip visible without under-bonnet; `TurnTracePanel` still gated
