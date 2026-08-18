# Conversational UI programme (C00–C14)

**Status:** MVP green (C00–C07 on Alex) · **C09 harness green / LLM 🟡** — C08 deferred · **C09b specified** (focus vs radar; C09 implements) · **C10 deferred** (scaffold landed; r3f + live feeds after SEC-04 event plumbing; not on HomePage) · **C11 future** (tone memory after C09 LLM proof) · **C12 landed** (Life Scripts CLI; first episodes green) · **C13 todo** (repeat the same life against Fireworks) · **C14 in_progress** (activity stream spec + v0 strip; assistant-ui wrap later)  
**Programme observability:** UI 🟢 frozen · Disclosure 🟢 active · Cortex 💤 deferred · Conversation activity 🟡 v0 strip (not SSE)  
**North star:** UI is a thin conversational projection of world state; chat history is not truth.

> **Pivot (2026-08-17):** Stop expanding C05b/c regex phrase families. [C09](./C09-llm-conversational-boundary.md) supersedes language parsing with LLM tool calling ([ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md)). `intent_router` is frozen as fallback / test oracle.
>
> **C05d fence (confirmed):** conversation context **MAY** carry forward intent, **MAY** modify horizon, **MAY** preserve requested cardinality. World state is **ALWAYS** queried again, **NEVER** inferred from the previous answer. Once green, only three discourse modifiers: `"this week?"`, `"tomorrow?"`, `"and after that?"` — then **stop teaching the router English**. C05–d = deterministic capability + regression scaffold; C09 = normal human conversation. Do not add more phrase families.

## Three architectural rules (non-negotiable)

### 1. Attention `context` ≠ WORTH DOING

```typescript
type AttentionState = {
  simulated_time: string;
  needs_you: AttentionItem[];     // attention policy: surface
  context: AttentionItem[];       // attention policy: context
  next_actions: NextActionView[]; // separate support / next-action layer
  can_wait_summary?: CanWaitSummary;
  presentation: PresentationPlan;
};
```

| Policy decision | Attention bucket | Next Action layer |
| --- | --- | --- |
| `surface` | `needs_you` | (optional, separate) |
| `context` | `context` | may suggest WORTH DOING — **not** by remapping the array |
| `suppress` | `can_wait` | — |

Token-audit: attention → **CONTEXT**; next-action → **“Unblocked now”** in `next_actions[]`.

### 2. Silence = absence, not a message type

```
presentation.proactive_silence
  → audit / debug event log records evaluation
  → conversation[] unchanged
```

No empty proactive turn. No invisible chat item.

### 3. Evaluation observes Enigma; Demo API does not depend on it

```
              shared projection (packages/attention)
                     ↑              ↑
                     │              │
                 Demo API       Evaluation
                     ↑
                 Simulation
```

C00 may use evaluation artifacts **only** to establish parity during development. Runtime: `apps/api` → `packages/attention` + `packages/fixtures`, never `packages/evaluation`.

## Tickets

| Ticket | Title | Status |
| --- | --- | --- |
| [C00](./C00-demo-attention-projection.md) | Demo attention projection backend | done |
| [C01](./C01-conversation-shell.md) | Conversation shell | done |
| [C02](./C02-enigma-client.md) | EnigmaClient + types | done |
| [C03](./C03-demo-time-machine.md) | Demo time machine | done |
| [C04](./C04-attention-primitives.md) | Attention primitives + presentation | done |
| [C05](./C05-conversation-intents.md) | Deterministic intents | done |
| [C05b](./C05b-natural-language-intents.md) | Natural-language intents + availability | done |
| [C05c](./C05c-relative-availability.md) | Relative availability + typo tolerance | done |
| [C05d](./C05d-conversation-continuity.md) | Conversational continuity + follow-ups | done (language fenced) |
| [C05e](./C05e-recent-source-queries.md) | Recent source queries (email, etc.) | todo |
| [C06](./C06-provenance-debug.md) | Provenance + qualification debug | done |
| [C07](./C07-assist-proposals.md) | Assist proposal UI | done |
| [C07b](./C07b-assist-completed-not-task-completed.md) | ASSIST COMPLETED ≠ TASK COMPLETED | **in_progress** |
| [C08](./C08-live-enigma-client.md) | LiveEnigmaClient (deferred) | todo |
| [C09](./C09-llm-conversational-boundary.md) | LLM tool-calling orchestrator | harness green · LLM 🟡 |
| [C09b](./C09b-discourse-focus.md) | Discourse focus vs objects in the response | **specified** (Life Script contract; C09 implements) |
| [C10](./C10-cortex-brain-visualizer.md) | Cortex brain visualizer (observability) | **deferred** (scaffold landed; r3f + live feeds after SEC-04) |
| [C11](./C11-tone-memory.md) | Tone memory (how to speak, not who you are) | **future** (after C09 LLM proof) |
| [C12](./C12-life-scripts.md) | Life Scripts (Alex episodes as product tests) | **landed** (CLI; UI player later). Later months: [D08f-scripts](../demo-scenario/D08f-scripts.md) — do not implement C11 |
| [C13](./C13-life-script-reliability.md) | Life Script reliability (repeat Fireworks runs) | **todo** |
| [C14](./C14-conversation-activity-stream.md) | Conversation activity stream (real events, not fake CoT) | **in_progress** (spec + v0 strip) |
| [C34](./C34-relational-bootstrap.md) | Relational bootstrap (continuation mechanics) | **frozen** ([#99](https://github.com/oscarhilton/enigma-assistant-/pull/99)) |
| [C35](./C35-goose-pixel-licence.md) | Goose pixel licence (work presence; C34 expressiveness) | **done** |

## First milestone (Alex)

Demo conversation helps Alex from **world state**, not a compiled biography. Source fragments may feel like a mystery; leftover shadow must stay a terrible detective novel ([SEC-07](../security/SEC-07-shadow-reconstruction-benchmark.md)).

1. Launch Demo · Jan 19 10:00  
2. “What needs me?” → real structured answer  
3. Inspect Why? / qualification debug  
4. Advance to Jan 20  
5. Ask again → answer changes because **world state** changed  

6. “Can you help me do that?” → Assist propose → approve → verified ack (C07)

## Next slice

**C14** — show what Enigma is actually doing (activity strip / later assistant-ui on Vite). **C13** — same Life Script YAML, `--live --runs 5`, reliability not a new biography. **C05e** — recent source queries (email recency tool). **C08** — LiveEnigmaClient when Private transport is ready. Live Demo conversation uses C09 when `FIREWORKS_API_KEY` (preferred) or `OPENAI_API_KEY` is set. Force the frozen router with `ENIGMA_DEMO_LLM_CONVERSATION=0` or `LLM_DISABLED=1`.

**Not next — shareable recipes.** Executive-function patterns as inspectable **declarative procedures** ([ADR-024](../../docs/adr/024-shareable-recipes-procedure-never-personal-state.md) · [shareable-recipes.md](../../docs/architecture/shareable-recipes.md) · [REC00](../recipes/REC00-shareable-recipes-north-star.md)) wait on **C09 LLM proof** (not harness-only) and **SEC-05 PASS**. Not executable code, not a prompt bundle. Do not implement a recipe engine, `enigma://` scheme, or calendar-join flow in C05e/C08/C10. LLM may later *match* a recipe id; Enigma still executes deterministically (ADR-020). New recipe versions re-evaluate capabilities (v1 grant does not silently authorise v2 `email.send`).

**Not next — tone memory.** How Enigma speaks ([ADR-025](../../docs/adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [tone-memory.md](../../docs/architecture/tone-memory.md) · [C11](./C11-tone-memory.md)) waits on **C09 LLM proof**. Style enums, not a psych dossier, not last-N chat as memory. Do not implement a tone store or C09 payload field in C05e/C08/C10. Distinct from [N03](../next-action/N03-preference-learning.md) Next Action fitness.

## Before real personal data (Gmail)

Conversational live paths on **Private roots** must not connect Oscar's inbox until the [SEC programme](../security/) passes [SEC-05](../security/SEC-05-personal-data-pilot-gate.md):

```text
C09 → SEC-00 → SEC-01 → SEC-02 → SEC-03 → SEC-04 → SEC-06 → SEC-05 PASS → Oscar's inbox
```

- [ADR-021](../../docs/adr/021-personal-data-security-boundary.md) — untrusted LLM, trusted Enigma Core; email is hostile input
- [data-retention.md](../../docs/architecture/data-retention.md) — retention zones, red-line reconstructability test, memory decay, forget operations
- [personal-data-security.md](../../docs/architecture/personal-data-security.md) — threat model, egress gate, `gmail.readonly` v0-real
- C05e/C08 live wiring must respect raw-source TTLs and route remote inference through SEC-02 egress gate on Private data

M11 Gmail ingestion scaffold is **not** sufficient for live mailbox connection.

## Docs

- [docs/architecture/conversational-ui.md](../../docs/architecture/conversational-ui.md)
- [docs/architecture/conversational-stream.md](../../docs/architecture/conversational-stream.md) · [C14](./C14-conversation-activity-stream.md)
- [docs/architecture/tone-memory.md](../../docs/architecture/tone-memory.md) · [C11](./C11-tone-memory.md) (`future`)
- [docs/architecture/cortex-visualizer.md](../../docs/architecture/cortex-visualizer.md) · [C10](./C10-cortex-brain-visualizer.md)
- [ADR-020 — LLM conversational boundary](../../docs/adr/020-llm-conversational-boundary-not-truth.md)
- [ADR-027 — Streaming presentation adapter](../../docs/adr/027-streaming-presentation-adapter.md)
- [ADR-021 — Personal data security boundary](../../docs/adr/021-personal-data-security-boundary.md) · [SEC programme](../security/)
- [ADR-024 — Shareable recipes](../../docs/adr/024-shareable-recipes-procedure-never-personal-state.md) · [REC00](../recipes/REC00-shareable-recipes-north-star.md) (`future`)
- [ADR-025 — Tone memory](../../docs/adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [C11](./C11-tone-memory.md) (`future`)
- [ADR-039 — Goose pixels project work](../../docs/adr/039-goose-pixels-project-work-not-mascot.md) · [C35](./C35-goose-pixel-licence.md)
- R-L10 findings · ADR-010 Next Action ≠ Attention
