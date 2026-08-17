# Conversational UI programme (C00–C31)

**Status:** MVP green (C00–C07 on Alex) · **C09 harness green / LLM 🟡** — C08 deferred · **C09b specified** (focus vs radar; C09 implements) · **C10 deferred** (scaffold landed; r3f + live feeds after SEC-04 event plumbing; not on HomePage) · **C11 future** (tone memory after C09 LLM proof) · **C12 landed** (Life Scripts CLI; first episodes green · PR [#89](https://github.com/oscarhilton/enigma-assistant-/pull/89) Python CI red) · **C13 todo** (repeat the same life against Fireworks) · **C14 done** (v0 activity strip merged [#90](https://github.com/oscarhilton/enigma-assistant-/pull/90); SSE/assistant-ui remaining) · **C09c landed · frozen** (conversation capsule; ADR-030) · **C15 in_progress** (ADR-029 handoff / `"ffs"` AC local; not in [#92](https://github.com/oscarhilton/enigma-assistant-/pull/92); C09c frozen) · **C16 in_progress** (attested completion invalidates next-action) · **C17–C22 todo/future** · **C23 landed · frozen as a specification** (gate red until C16–C21) · **C24 future** (read-only evidence worker after P0; [ADR-033](../../docs/adr/033-bounded-subtask-workers.md)) · **C25 in_progress** (evidence coverage bundle + courier / Goose projection; [ADR-034](../../docs/adr/034-evidence-coverage-bundle.md))  
**Programme observability:** UI 🟢 frozen · Disclosure 🟢 active · Cortex 💤 deferred · Conversation activity 🟡 v0 strip + courier (not SSE)  
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
| [C05e](./C05e-recent-source-queries.md) | Recent source queries (email, local WhatsApp quote) | landed |
| [C06](./C06-provenance-debug.md) | Provenance + qualification debug | done |
| [C07](./C07-assist-proposals.md) | Assist proposal UI | done |
| [C07b](./C07b-assist-completed-not-task-completed.md) | ASSIST COMPLETED ≠ TASK COMPLETED | **in_progress** |
| [C08](./C08-live-enigma-client.md) | LiveEnigmaClient (deferred) | todo |
| [C09](./C09-llm-conversational-boundary.md) | LLM tool-calling orchestrator | harness green · LLM 🟡 |
| [C09b](./C09b-discourse-focus.md) | Discourse focus vs objects in the response | **specified** (Life Script contract; C09 implements) |
| [C09c](./C09c-conversation-capsule.md) | Conversation capsule loop | **landed · frozen** (ADR-030; inherit frame, not authority) |
| [C10](./C10-cortex-brain-visualizer.md) | Cortex brain visualizer (observability) | **deferred** (scaffold landed; r3f + live feeds after SEC-04) |
| [C11](./C11-tone-memory.md) | Tone memory (how to speak, not who you are) | **future** (after C09 LLM proof) |
| [C12](./C12-life-scripts.md) | Life Scripts (Alex episodes as product tests) | **landed** (CLI; UI player later · [#89](https://github.com/oscarhilton/enigma-assistant-/pull/89) CI red). Later months: [D08f-scripts](../demo-scenario/D08f-scripts.md) — do not implement C11 |
| [C13](./C13-life-script-reliability.md) | Life Script reliability (repeat Fireworks runs) | **todo** |
| [C14](./C14-conversation-activity-stream.md) | Conversation activity stream (real events, not fake CoT) | **done** (v0 · [#90](https://github.com/oscarhilton/enigma-assistant-/pull/90); SSE/assistant-ui remaining) |
| [C15](./C15-semantic-bootstrap-capsule.md) | ADR-029 handoff: frustration after unsatisfied private request (bootstrap already landed) | **in_progress** (AC local; not in [#92](https://github.com/oscarhilton/enigma-assistant-/pull/92); C09c frozen) |
| [C16](./C16-attested-completion-invalidates-next-action.md) | Attested completion materializes; next_action cannot resurface | **todo** (P0) |
| [C17](./C17-execution-receipts-verification-ledger.md) | Execution receipts + “did you do it?” ledger | **todo** (P0 · ADR-032) |
| [C18](./C18-active-thread-record.md) | Active thread record (sibling of capsule) | **todo** (P1) |
| [C19](./C19-multi-intent-decompose.md) | Multi-intent decompose + unsupported reporting | **todo** (P1) |
| [C20](./C20-capability-contract-on-wire.md) | Capability contract on the compiled wire | **todo** (P1) |
| [C21](./C21-grounded-values-no-invented-facts.md) | Grounded values; no invented private facts | **todo** (P1) |
| [C22](./C22-adhd-response-shape.md) | ADHD-hostile response shape (one / one / one) | **future** (P2 · do not block P0) |
| [C23](./C23-continuity-integrity-life-script.md) | Continuity + action-integrity Life Script (61-turn gate) | **in_progress** (dump attached · YAML authored · gate red until C16–C21) |
| [C24](./C24-read-only-evidence-worker.md) | Read-only evidence worker (`"ffs"` path) | **future** (after P0 · ADR-033) |
| [C25](./C25-evidence-coverage-bundle.md) | Evidence coverage bundle + courier / Goose projection | **in_progress** (ADR-034) |
| [C26](./C26-grounded-assertions-epistemics.md) | Grounded assertions, epistemic status, and challenge/reconciliation | **todo** |
| [C27](./C27-handoff-turn-contract.md) | Handoff and turn contract | **todo** |
| [C28](./C28-event-spine-agent-work.md) | Event spine and agent-work lifecycle | **todo** |
| [C29](./C29-life-memory-and-retention.md) | Life memory, retention gate, and third-party ethics | **todo** |
| [C30](./C30-brain-cortex-case-file.md) | Brain, Cortex, and Case File projections | **todo** |
| [C31](./C31-goose-work-projection-and-proactivity.md) | Goose work projection and proactivity timing | **todo** |

## First milestone (Alex)

Demo conversation helps Alex from **world state**, not a compiled biography. Source fragments may feel like a mystery; leftover shadow must stay a terrible detective novel ([SEC-07](../security/SEC-07-shadow-reconstruction-benchmark.md)).

1. Launch Demo · Jan 19 10:00  
2. “What needs me?” → real structured answer  
3. Inspect Why? / qualification debug  
4. Advance to Jan 20  
5. Ask again → answer changes because **world state** changed  

6. “Can you help me do that?” → Assist propose → approve → verified ack (C07)

## Next slice

**Conversation Continuity and Action Integrity (C16–C23) — before more assists.** The attention spine is promising; the conversational layer and authoritative world state still behave like separate systems. P0: attested completion must leave `next_action.get` ([C16](./C16-attested-completion-invalidates-next-action.md)); external-action claims need an execution receipt and “did you do it?” inspects the ledger, never `assist.propose` ([C17](./C17-execution-receipts-verification-ledger.md) · [ADR-032](../../docs/adr/032-action-ledger-execution-receipts-verification.md)). P1: active-thread sibling of the frozen capsule ([C18](./C18-active-thread-record.md)); multi-intent decompose ([C19](./C19-multi-intent-decompose.md)); capability contract on the wire ([C20](./C20-capability-contract-on-wire.md)); no invented private facts ([C21](./C21-grounded-values-no-invented-facts.md)). P2 response shape ([C22](./C22-adhd-response-shape.md)) is `future` and must not block P0. Sprint gate: [C23](./C23-continuity-integrity-life-script.md). Do **not** reopen [C09c](./C09c-conversation-capsule.md) (landed · frozen). Do **not** fold this sprint into [C15](./C15-semantic-bootstrap-capsule.md) live bootstrap.

**Not this sprint — bounded workers ([ADR-033](../../docs/adr/033-bounded-subtask-workers.md)).** One agent speaks; specialist hands (evidence, decompose, explain, verify) sit behind the compiler. They do not replace P0 invariants. First worker is a read-only evidence fetch on the `"ffs"` path ([C24](./C24-read-only-evidence-worker.md), `future` until C16+C17 `done`). No extra conversational personalities.

**Still in flight, not this sprint:** **C14 later slices** — dual SSE / assistant-ui on Vite (v0 strip is merged). **C13** — same Life Script YAML, `--live --runs 5`. **C15** — land the ADR-029 `"ffs"` handoff (local AC green; not in PR #92). **C08** — LiveEnigmaClient when Private transport is ready. Live Demo conversation uses C09 when `FIREWORKS_API_KEY` (preferred) or `OPENAI_API_KEY` is set. Force the frozen router with `ENIGMA_DEMO_LLM_CONVERSATION=0` or `LLM_DISABLED=1`.

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
- [ADR-032 — Action ledger / execution receipts / verification-not-action](../../docs/adr/032-action-ledger-execution-receipts-verification.md)
- [ADR-033 — Bounded subtask workers](../../docs/adr/033-bounded-subtask-workers.md)
- [ADR-027 — Streaming presentation adapter](../../docs/adr/027-streaming-presentation-adapter.md)
- [ADR-021 — Personal data security boundary](../../docs/adr/021-personal-data-security-boundary.md) · [SEC programme](../security/)
- [ADR-024 — Shareable recipes](../../docs/adr/024-shareable-recipes-procedure-never-personal-state.md) · [REC00](../recipes/REC00-shareable-recipes-north-star.md) (`future`)
- [ADR-025 — Tone memory](../../docs/adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [C11](./C11-tone-memory.md) (`future`)
- R-L10 findings · ADR-010 Next Action ≠ Attention
