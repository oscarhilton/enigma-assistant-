# ADR-027: Streaming presentation adapter — assistant-ui on Vite, Enigma remains the agent

**Status:** Accepted  
**Date:** 2026-08-17

> **Enigma shouldn't tell you that it's thinking. It should quietly show you what it's actually doing.**

## Context

The conversational MVP (C00–C07) renders a completed `ConversationItem[]` after `POST /demo/conversation/message`. C09’s orchestrator is still request/response: tool hops exist on `llm_trace` only after the turn returns. Under-bonnet `TurnTracePanel` already shows the forensic hop list. Cortex ([C10](../../tickets/conversational-ui/C10-cortex-brain-visualizer.md)) projects overlapping audit feeds into a debug/3D view — deferred, not the in-thread product surface.

Presentation is now part of the product: Claude-Code-like activity (Read/Edit files) but with **human-facing labels from real Enigma events**, never fake chain-of-thought. The industry default for that UI is assistant-ui + Vercel AI SDK, usually on Next.js. Adopting that stack as **backend architecture** would move orchestration, tool execution, and “agent state” into Vercel’s `streamText` / `useChat` world — which [ADR-020](./020-llm-conversational-boundary-not-truth.md) forbids.

`apps/web` is a Vite React SPA. Rewriting it to Next solely because assistant-ui’s blog posts use Next is not a product requirement.

## Decision

1. **FastAPI / Enigma Core stays the agent** — truth, event source, orchestration, policy, execution. Remote models understand and speak; they do not become the runtime.
2. **assistant-ui is a presentation adapter on Vite.** Use `@assistant-ui/react` primitives (streaming viewport, custom tool-call / activity renderers, composer) inside `apps/web`. Do not migrate the app to Next.js. Do not use assistant-ui’s `"use generative"` Vite plugin to run tools in the web server — tools stay in Core.
3. **Wire format is Enigma-native**, not Vercel UI-message `data-*` parts as source of truth. Stream **two concurrent streams**: machine activity events + human prose deltas. A thin client adapter may later *speak* assistant-ui’s runtime APIs (`ExternalStoreRuntime` now, `AssistantTransport` when Core streams agent snapshots).
4. **Three projections of the same event** — NORMAL (one line), CURIOUS (collapsed ✓ list), FORENSIC (existing `TurnTracePanel` / egress disclosure / Cortex). Do not invent a parallel cognition log.
5. **C09 token streaming is a follow-on.** C14 specifies the UI and v0-projects completed `llm_trace` hops. Fireworks SSE / orchestrator streaming does not block the spec.

## Consequences

- Activity copy is a pure function of Core events (`availability.checked` → “Checked your calendar”). No “Thinking carefully…”
- Assist states are cards (PROPOSED → APPROVED → EXECUTING → VERIFIED), not theatre.
- Progressive ◌ → ✓ may hold a row for hundreds of ms for perception; it must not delay tool execution.
- Cortex remains forensic/3D and read-only. Conversation activity is the human-facing layer of the same hops ([conversational-stream.md](../architecture/conversational-stream.md)).
- Installing `@assistant-ui/react` waits on a clean viewport wrap (later C14 slice). Spec + types + activity-strip stub land first.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Next.js rewrite + AI SDK `streamText` as the agent | Violates ADR-020; Enigma would no longer be truth/orchestration |
| Canonical wire = Vercel AI SDK data-stream protocol | FastAPI impersonating a Vercel route; event vocabulary becomes `data-*` parts |
| Custom chat components forever | Reimplement streaming, a11y, tool renderers that assistant-ui already has |
| assistant-ui requires Next | `@assistant-ui/react` runs in a Vite SPA; Next is their demo default, not a constraint |
| AssistantTransport as the first slice | Needs a streaming Core endpoint C09 does not have yet; ExternalStore over existing items is enough until then |
| Fake latency / fake CoT to feel “alive” | Lies about what Enigma did; forbidden by the product principle |

## Related

- [conversational-stream.md](../architecture/conversational-stream.md)
- [conversational-ui.md](../architecture/conversational-ui.md)
- [ADR-020](./020-llm-conversational-boundary-not-truth.md)
- [C14](../../tickets/conversational-ui/C14-conversation-activity-stream.md)
- [C09](../../tickets/conversational-ui/C09-llm-conversational-boundary.md) — stream/events follow-on
- [C10](../../tickets/conversational-ui/C10-cortex-brain-visualizer.md) — forensic/3D, same events
