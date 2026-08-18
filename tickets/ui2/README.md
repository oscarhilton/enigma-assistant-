# UI2 — Enigma v2 launchpad

**North star:** Start familiar. Make it excellent. Let Enigma earn its uniqueness.

**Product:** Make safe agency feel obvious, bounded, and delightful.

**UI:** Show what matters, what Enigma is doing, and why — without requiring users to understand architecture.

## Hard requirements (v2 launchpad)

1. **Streaming responses** — first-class token/chunk streaming; text stream and AgentWork stream are **independent channels** (C35 honest)
2. **shadcn-style UI** — restrained primitives, typography, spacing
3. **Basically ChatGPT** — conversation-first, sidebar/history, bottom composer, minimal chrome

## Architecture rules

- **v2 beside v1** — do NOT mutate v1 into v2. Route `/v2/*` behind pilot flag or separate entry. v1 remains reference, not dependency.
- **Read-model driven** — UI consumes explicit projections (`TodayProjection`, `CaseProjection`, `AssistantTurn`, `AgentWorkSnapshot`, `WhyProjection`, etc.); no semantic reconstruction in React
- **Fossil policy** — classify v1 components KEEP / REIMPLEMENT / DELETE / UNKNOWN; matching v1 behaviour not required unless Life Script says so
- **Forensic honesty** — Unavailable semantic state must render as unavailable — never reconstructed or guessed by the frontend.

## Converge order (intended)

This is sequencing for agents. It does not authorise merging PRs.

1. [#113](https://github.com/oscarhilton/enigma-assistant-/pull/113) UI2-01 shell (`ticket/UI2-01-v2-shell`)
2. [#115](https://github.com/oscarhilton/enigma-assistant-/pull/115) UI2-02 streaming (`ticket/UI2-02-streaming`)
3. UI2-03/04 shadcn + continuity
4. [#114](https://github.com/oscarhilton/enigma-assistant-/pull/114) UI2-DEBUG rebased onto the resulting shell

**Rationale:** streaming and continuity alter the turn/session data Debug wants to observe. Debug can land earlier if conflict-light and independently useful; do not contort streaming/continuity around #114.

Once UI2-02 lands, the first Debug wiring is two **parallel lanes** (not reconstructed), side-by-side, from real stream events only:

```
ASSISTANT OUTPUT
chunk → chunk → chunk → complete

AGENT WORK
investigating → advancing → waiting / verifying → handled
```

## Forensic copy bundles

Every paste starts with:

```
ENIGMA FORENSIC SNAPSHOT
Build: …
World: …
Turn: …
Privacy level: SAFE|DETAILED|LOCAL
```

## Deferred (explicit in tickets — do NOT implement until claimed)

Today dashboard, rich Cases workspace, Memory Explorer, Shadow visual language, Goose habitat, bespoke IA, complex agent panels, distinctive visual system

## Tickets

| ID | Title | Status |
| --- | --- | --- |
| [UI2-01](./UI2-01-v2-shell.md) | v2 shell + world switch + persistent Assistant + build identity + existing Goose | `done` |
| [UI2-02](./UI2-02-streaming.md) | True response streaming (incremental, cancel, reconnect; work stream independent) | `done` |
| [UI2-03](./UI2-03-shadcn-foundation.md) | shadcn component foundation | `done` |
| [UI2-04](./UI2-04-conversation-continuity.md) | Conversation continuity (thread, history, world-switch isolation, C34 survives streaming) | `done` |
| [UI2-05](./UI2-05-inspectability-minimal.md) | Inspectability minimal (Goose click / Why compact sheet — no Cortex on surface) | `done` |
| [UI2-06](./UI2-06-alex-life-scripts.md) | Alex Life Scripts through v2 (Brunch, Monday/Maya, HONK HONK, FALSE VICTORY, Forget) | `done` |
| [UI2-07](./UI2-07-real-pilot.md) | Real pilot (P03 calendar dogfood) | `todo` |
| [UI2-DEBUG](./UI2-DEBUG-semantic-forensics.md) | Semantic Forensics — turn snapshot, Turn Contract, Evidence, Handoff, AgentWork, Authority, egress, streaming trace, Memory impact; Copy bug report (Safe/Detailed/Local forensic tiers); ⌘⇧D; "Why not?" | `done` |

Branch pattern: `ticket/UI2-xx-slug`
