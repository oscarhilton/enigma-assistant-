# UI2 — Enigma v2 launchpad

**North star:** Start familiar. Make it excellent. Let Enigma earn its uniqueness.

**Product:** Make safe agency feel obvious, bounded, and delightful.

**UI:** Show what matters, what Enigma is doing, and why — without requiring users to understand architecture.

## Constitutional invariants

These are non-negotiable. Every UI2 ticket must preserve them.

| Invariant | Meaning |
| --- | --- |
| **PROSE ≠ AgentWork** | Assistant text stream and AgentWork stream are independent channels. Goose/work state must not be inferred from partial prose. |
| **STOP GENERATING ≠ cancel work** | Stop aborts prose streaming only. In-flight AgentWork continues, reconciles, or fails honestly — it is not silently cancelled. |
| **THREAD HISTORY is world-scoped** | Thread lists and active thread persist per world (Alex Lab ↔ My Enigma). No cross-world leakage on switch or refresh. |
| **DEBUG reports captured state ≠ invents missing state** | Forensics render what was observed on the wire. Unavailable semantic state shows as unavailable — never reconstructed or guessed by the frontend. |

## Hard requirements (v2 launchpad)

1. **Streaming responses** — first-class token/chunk streaming; text stream and AgentWork stream are **independent channels** (C35 honest)
2. **shadcn-style UI** — restrained primitives, typography, spacing
3. **Basically ChatGPT** — conversation-first, sidebar/history, bottom composer, minimal chrome

## Architecture rules

- **v2 beside v1** — do NOT mutate v1 into v2. Route `/v2/*` behind pilot flag or separate entry. v1 remains reference, not dependency.
- **Read-model driven** — UI consumes explicit projections (`TodayProjection`, `CaseProjection`, `AssistantTurn`, `AgentWorkSnapshot`, `WhyProjection`, etc.); no semantic reconstruction in React
- **Fossil policy** — classify v1 components KEEP / REIMPLEMENT / DELETE / UNKNOWN; matching v1 behaviour not required unless Life Script says so

## Confirmed merge sequence (do not change)

This is sequencing for agents. It does not authorise merging PRs.

1. [#113](https://github.com/oscarhilton/enigma-assistant-/pull/113) UI2-01 shell (`ticket/UI2-01-v2-shell`)
2. [#115](https://github.com/oscarhilton/enigma-assistant-/pull/115) UI2-02 streaming + honest cancel/reconcile (`ticket/UI2-02-streaming`)
3. [#118](https://github.com/oscarhilton/enigma-assistant-/pull/118) UI2-03/04 shadcn + per-world continuity (`ticket/UI2-03-04-shadcn-continuity`)
4. Rebase [#114](https://github.com/oscarhilton/enigma-assistant-/pull/114) UI2-DEBUG semantic forensics onto that tip (`ticket/UI2-DEBUG-forensics`)

**Rationale:** #114 observes final turn/stream/session shape. Streaming and continuity must not conform to an earlier debugger — Debug rebases onto the stack tip.

Once UI2-02 lands, the first Debug wiring is two **parallel lanes** (not reconstructed), side-by-side, from real stream events only:

```
ASSISTANT OUTPUT
chunk → chunk → chunk → complete

AGENT WORK
investigating → advancing → waiting / verifying → handled
```

## Separate tracks (not part of UI2 conceptual stack)

| PR | Scope | Merge when |
| --- | --- | --- |
| [#125](https://github.com/oscarhilton/enigma-assistant-/pull/125) | World-aware 409 hydrate (supersedes #116) | Green + reviewed — independent of UI2 stack |
| [#117](https://github.com/oscarhilton/enigma-assistant-/pull/117) | Programme notes (this doc) | Whenever convenient |

## UI2-06 Life Scripts graduation test

The UI2 stack (#113 → #115 → #118 → #114, plus UI2-05/06) landed via [#122](https://github.com/oscarhilton/enigma-assistant-/pull/122). **[UI2-06](./UI2-06-alex-life-scripts.md)** replays five P02 Life Scripts through `/v2`.

**Level 1 only.** Hugging Face full Alex corpus is **out of scope** for UI2-06. That is boot Level 2 — [P04 Alex Full-Life Reprime](../pilot/P04-alex-full-life-reprime.md) ([data-boot.md](../../docs/architecture/data-boot.md)). Do not download HF, do not fold messy life into these five scripts, do not load a prebuilt Alex brain. **P04 does not start until UI2-06 is pilot-grade** (Goose basic flight certification).

| Script | What it proves in v2 |
| --- | --- |
| Brunch | calendar hold ≠ booking |
| Monday/Maya | challenge without invention |
| HONK HONK | relationship continuity |
| FALSE VICTORY | streaming/Goose cannot imply success |
| Forget | no resurrection |

Plus world switching and thread isolation around them.

**Freeze bar:** Every constitutional Life Script must work in UI2, and every failure must produce a useful forensic snapshot without requiring console archaeology.

**Development loop:** Oscar opens `/v2` → Goose moves → something streams → something weird → ⌘⇧D → Copy → paste for diagnosis.

## Forensic copy bundles

Every paste starts with:

```
ENIGMA FORENSIC SNAPSHOT
Build: …
World: …
Turn: …
Privacy level: SAFE|DETAILED|LOCAL
```

When a Life Script fails, one copied forensic bundle (Safe / Detailed / Local) should explain why — diagnosable by construction.

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
| [UI2-06](./UI2-06-alex-life-scripts.md) | Alex Life Scripts through v2 (Brunch, Monday/Maya, HONK HONK, FALSE VICTORY, Forget) — **Level 1 only; HF corpus out of scope** | `done` |
| [UI2-07](./UI2-07-real-pilot.md) | Real pilot (P03 calendar dogfood) | `todo` |
| [UI2-DEBUG](./UI2-DEBUG-semantic-forensics.md) | Semantic Forensics — turn snapshot, Turn Contract, Evidence, Handoff, AgentWork, Authority, egress, streaming trace, Memory impact; Copy bug report (Safe/Detailed/Local forensic tiers); ⌘⇧D; "Why not?" | `done` |

Branch pattern: `ticket/UI2-xx-slug`
