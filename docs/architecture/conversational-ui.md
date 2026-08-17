# Conversational UI architecture

Enigma’s product surface is a **thin conversational projection** of the world model. Chat history is not source of truth; **world state is**.

## Three layers (from R-L10)

The UI renders these as **separate backend concepts**. It never reconstructs one from another.

| Layer | Meaning | UI must not infer from |
| --- | --- | --- |
| **Qualification** | Does this belong in NEEDS YOU / context / CAN WAIT? | rank, score alone, presentation slot |
| **Ranking** | Order among eligible items | presentation order |
| **Presentation** | What reaches the user now | NEEDS YOU set size |

Production policy evaluates each candidate independently (`decide_interruption`), then ranks surfaced items.

## Attention ≠ Next Action (ADR-010)

```typescript
type AttentionState = {
  needs_you: AttentionItem[];      // policy decision === surface
  context: AttentionItem[];        // policy decision === context — NOT WORTH DOING
  next_actions: NextAction[];      // separate reasoning layer
  can_wait_summary?: CanWaitSummary;
  presentation: PresentationPlan;
};
```

**Do not map `context` → WORTH DOING.** The conversational layer may combine them in copy:

> Nothing needs you.  
> A good thing you could do: Token inventory is unblocked.

…without pretending the attention policy produced a Next Action.

Mum's birthday in three weeks may sit in `context[]` with **no** `next_actions[]` entry — relevant, not worth doing now.

## Silence is nothing in conversation

When `presentation.proactive_silence` is true:

- **Do not** append a conversation item
- Record in demo event log / time-machine panel only
- The transcript has no evidence anything happened

Silence is a product primitive, not a message type.

## EnigmaClient boundary

Demo and Live share one interface (`apps/web/src/enigma/client.ts`):

- `DemoEnigmaClient` → `/demo/*` + Alex simulation
- `LiveEnigmaClient` → Private core (deferred, C08)

Demo instrumentation (qualification debug, event log) is gated by Demo mode; renderers are shared.

## Runtime dependency rule

```
                 shared projection (packages/attention/projection.py)
                       ↑
                       │
Simulation ────────────┼──────── Demo API
                       │
Evaluation ────────────┘  (observe/replay only — not a runtime dep)
```

Evaluation snapshot utilities may establish parity during development. **Product runtime must not acquire `packages/evaluation` as a permanent dependency.** Shared projection logic lives in `packages/attention`.

## Flow

```
WORLD
  ↓
attention qualification ───→ NEEDS YOU
  ↓
next-action reasoning ──────→ WORTH DOING (next_actions[])
  ↓
presentation policy
  ↓
conversation (structured items)
  ↓
structured Assist
  ↓
approval / action
```

Demo mode is Alex living inside the same machine.

Cross-boundary coordination (future): Assist approval maps to the A0–A5 ladder ([ADR-019](../adr/019-delegated-authority-and-execution-ladder.md) · [enigma-coordination-protocol.md](./enigma-coordination-protocol.md)).

Shareable recipes (future, after C09 LLM proof + SEC-05): LLM understands intent → recipe describes **how** (declarative typed steps, not code, not a prompt pack) → Enigma supplies private truth → policy permits → Assist approval → executor verifies. Recipes contain procedure, never personal state ([ADR-024](../adr/024-shareable-recipes-procedure-never-personal-state.md) · [shareable-recipes.md](./shareable-recipes.md) · [REC00](../../tickets/recipes/REC00-shareable-recipes-north-star.md)). Do not implement in this programme.

Tone memory (future, after C09 LLM proof): send a **small style-enum profile** with `current_subject` and tool results — not the last 200 messages, not a psych dossier. USER-SET and LEARNED persist; TURN-LOCAL evaporates. **Tone may transform expression; it may not transform state, urgency, recommendation strength, or authority.** ([ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [tone-memory.md](./tone-memory.md) · [C11](../../tickets/conversational-ui/C11-tone-memory.md)). Do not implement in this programme until C11 unparks.

See also: [next-action.md](./next-action.md), [ADR-012](../adr/012-reasoning-value-gate-decision.md), [ADR-020](../adr/020-llm-conversational-boundary-not-truth.md), [ADR-027](../adr/027-streaming-presentation-adapter.md), [conversational-stream.md](./conversational-stream.md), R-L10 ticket.

## C09 conversational boundary

**The model understands and speaks. Enigma knows and acts.** ([ADR-020](../adr/020-llm-conversational-boundary-not-truth.md))

```
USER
  ↓
CONVERSATIONAL LLM          one boundary, two phases
  ├─ INTERPRET → ordinary conversation ─────────┐
  └─ tool request → ENIGMA CORE → structured    │
                         ↓                      │
                      RESPOND ←─────────────────┘
                         ↓
                       USER
```

Interpret and respond may be one loop or two model sizes. They are **not** a second personality LLM that polishes Enigma. That agent can turn `urgency: LOW` into “you should probably do this today.”

**Conversation state resolves language; tools establish truth.** Context may help the model understand the question. It may not answer the question. `CONVERSATION STATE` → interpretation authority; `TOOL RESULT` → factual authority.

**Hard C09 invariant:** A model may not answer a question about the user's private world from conversational context alone. It must ground the answer through an Enigma capability. `referent_candidates` (`{id, label, kind}`) are for referent resolution only — not timing, urgency, details, status, recommendations, or world claims.

Ordinary conversation (`sky`, `:)` , `wait`, `what`) is a lane, not a missing tool. Personal-world questions with no evidence still admit ignorance.

Life Scripts ([C12](../../tickets/conversational-ui/C12-life-scripts.md)) test both phases: capability selection **and** `response_meaning`. `"Okay."` is not an answer.

### Five lanes

Referent resolution sits under all five. It is not an action.

| Lane | Example | What holds |
| --- | --- | --- |
| **1. CONVERSATION** | `yeah :)` · `wait` | Speak. No capability. |
| **2. GENERAL KNOWLEDGE** | `how do design tokens work?` · `what is sushi?` · `yes but how` | Generic knowledge is allowed. No private-world invention. |
| **3. PRIVATE-WORLD QUERY** | Saturday plans | Enigma capability. Conversation state may not answer. |
| **4. EXTERNAL-WORLD QUERY** | sushi places in Shoreditch? | Search required. **Must not invent venues/addresses/prices.** Missing capability → defer, do not fake a table. |
| **5. ACTION** | book one | Propose → explicit approval affordance → verify. |

**The model may possess general knowledge. It may not manufacture current-world evidence.**

Speech acts do not collapse into `assist.propose`. Funnel ([ADR-028](../adr/028-conversational-constitution-attestation-dialogue-support.md)):

```
UNDERSTAND → SUPPORT → PREPARE → PROPOSE → APPROVE → EXECUTE
```

**Distress may increase supportiveness, never authority.** Ambiguous help requests default to the least-authoritative useful interpretation. `"help, I'm overwhelmed"` / `"I need help with that"` → SUPPORT. `"can you draft something for me?"` → PREPARE. `"do it"` → proposal + explicit approval, never silent execute.

User reports (`I've done the draft colours`) are evidence (`world.record_user_attestation`). Commands grant authority. Recent dialogue is 2–6 egress-filtered turns: recent chat helps interpret; it does not establish world truth.

**Yes inherits the speech act of the question it answers. It never upgrades that act.** SHOW? → yes → SHOW. Never SHOW? → yes → `assist.approve`. Core guard: `pending_dialogue_act` / `pending_confirmation`. Approval only if the previous Enigma turn created an explicit approval affordance.

**A conversational correction may change what Enigma is talking about; it may never by itself authorize Enigma to do something.** SUBJECT SELECTION ≠ CAPABILITY SELECTION.

Turn-local constraints (“we will be in Shoreditch”) evaporate like turn-local tone. They are not durable user memory and not an action.

Assist invariant: proposal surfaced → id stored authoritatively → conversation references the same id → approval resolves the same id.

Life Script: `packages/evaluation/scripts/alex_jan19_speech_acts.script.yaml`.

## Discourse focus ≠ objects in the response

Cards Enigma renders are not the conversation subject. `ConversationContext` (C09 — `conversation_context.py`) holds discourse focus:

```
ConversationContext
├─ current_subject_id
├─ current_subject_kind
├─ focus_reason
├─ pending_dialogue_act / pending_confirmation
│    SHOW_CONFIRMATION | APPROVE_CONFIRMATION | …
└─ turn_local_constraints   (session-only; evaporate; not memory)
```

```
objects_in_response[]  ≠  conversation_focus
```

Rendering “also on radar: brunch” must **not** steal focus from TOKEN. Focus is a discourse pointer, not “whatever structured item was last painted.”

| Transition | Focus |
| --- | --- |
| USER explicitly selects an item | change |
| MODEL answers primarily about an item | may change |
| HORIZON MODIFIER (`"this week?"`, `"what about the week after?"`) | **preserve** unless the response clearly replaces the subject |
| SECONDARY CARD RENDERED (radar / “also on radar”) | **do not** change |
| FAILED / UNKNOWN TURN | **do not** change |
| EMPTY HORIZON (`agenda.get` next week with nothing on it) | **do not** change — leftover `referent_candidates` stay resolvable, not focus |

`referent_candidates` may bind “the dinner” / “the parents” to an id. They must not become `current_subject` merely by existing after an empty agenda.

**A tool result may be an intermediate fact.** Duration answers “how long”, not “when should I do it?” or “like now?”. The orchestrator continues with `availability.check` until the question is answered. `"Saturday? I think?"` is a horizon / `temporal_constraint`, not a duration query. `"Are you sure there's nothing more important?"` re-queries `attention.get_current` — confidence from comprehension, not wording.

Life Script: `packages/evaluation/scripts/alex_jan19_when_should_i.script.yaml`.

Jan 19 10:00 shape this protects:

1. `"What is urgent right now?"` → focus = TOKEN (`item-obligation_token_audit`)
2. `"this week?"` → horizon changes; brunch may appear as a secondary object; focus stays TOKEN
3. `"what about the week after?"` → another horizon; focus stays TOKEN
4. `"What is the draft colour?"` → lexical recovery to TOKEN (C09, not regex)
5. `"Can you help me do that?"` → Assist TOKEN. If brunch stole focus, this is the bug.
6. `"Can you help me do the token inventory"` → named referent + explicit do → Assist TOKEN
7. `"Can you help me do the design tokens"` with brunch in focus → Assist TOKEN, not brunch
8. `"I need help with that"` / `"help, I'm overwhelmed"` → SUPPORT (`world.explain`), not Assist. Ambiguous help requests default to the least-authoritative useful interpretation.
9. `"help!"` / `"heeeelllppp!!"` → ordinary social conversation, **no** Assist. Do not add these to `intent_router`.
10. Delayed `"Done — Saturday brunch is booked"` → attributed to the originating Assist via parent correlation; must not appear as a reply to the current user turn. Update the Assist card, not conversational prose.

Life Script: `packages/evaluation/scripts/alex_jan19_focus_vs_radar.script.yaml` ([C12](../../tickets/conversational-ui/C12-life-scripts.md) · [C09b](../../tickets/conversational-ui/C09b-discourse-focus.md)). Public-effect keys: `preserve_subject`, `secondary_items` / `secondary_items_may_include`, `assist_target`, `attributed_to_original_assist`. No router intents, handler names, or regex.

**Conversational references may be implicit; approvals must resolve to an explicit capability object before execution.** Queries (`world.explain`, `attention.get_current`) may omit ids. `assist.propose` / `assist.approve` may arrive as `{}` on the model tool request; Enigma binds `target_id` / `proposal_id` before execution and the LLM trace must show:

```
MODEL TOOL REQUEST  assist.propose({})
REFERENT RESOLUTION named_referent → item-obligation_token_audit
EXECUTED TOOL REQUEST assist.propose({target_id: item-obligation_token_audit})
```

Empty propose must not blindly execute `current_subject` when the user named a different referent (brunch in focus + `"Can you help me do the design tokens"` → TOKEN, not brunch). `assist.approve({})` binds `current_assist_proposal_id` or fails — the executed request always carries `proposal_id`.

`focus_reason` and parent-correlation Assist completion are C09 work — not taught to the frozen router, not a polish LLM.

## Assist completed ≠ task completed

Verified Assist is not the same as completing the underlying obligation. C09 was right to trust tools; the bug is Enigma world semantics if a draft Assist **SATISFIES** TOKEN.

```text
understand → help → verify → update world → derive new state → derive new next action
```

| Effect | Meaning | Demo example |
| --- | --- | --- |
| **SUPPORT_ONLY** | Prepared something; obligation remains | (unused in v1 Demo) |
| **ADVANCES** | New support state; recalculate next action | TOKEN draft → IN_PROGRESS / DRAFT_READY → “Review the draft” |
| **SATISFIES** | Verified effect completes the obligation | Brunch booked |
| **UNRELATED** | Side effect does not mutate the target | — |

`current_subject_id` may survive completion (“what did you just do?”). `current_next_action_id` must not point at a non-action. Focus vs product projection have separate lifetimes — same family as `objects_in_response[] ≠ conversation_focus`.

**Absence of recommendation is not evidence of absence of worthwhile activity.** Empty `next_action_ids` ≠ “Nothing worth doing.” Prefer “Nothing stands out as a strong next action.” Brunch and Atlas can still be in context.

Life Script: `packages/evaluation/scripts/alex_jan19_assist_lifecycle.script.yaml` ([C07b](../../tickets/conversational-ui/C07b-assist-completed-not-task-completed.md)).

## Life Scripts (C12)

Life Scripts are **literal multi-turn episodes of Alex's life** played through the real conversational surface. They test Enigma-as-product — `"Nah, can't be arsed. Anything else?"` — not `intent=GET_NEXT_ACTION`.

If Enigma passes the life, the internals are allowed to change.

| Rule | Meaning |
| --- | --- |
| Speak like Alex | Natural speech in the script; no router intents / orchestrator branches / handler names |
| Public effects | Assert capability boundary, subject, world mutation, privacy, authority, `must_not` |
| Replaceable model | Same YAML: deterministic Scripted LLM (CI) or live Fireworks (proof) |
| Understanding ≠ not-fallback | Ordinary conversation has a `response_meaning` contract. `"Okay."` is not an answer. |

YAML `v1: live` means the turn is on the C09 v1 **product surface** (an active turn). It is not Fireworks. Deferred turns (`assist.explain`, `attention.can_wait`, source-scoped attention) record a missing product capability instead of cheating the suite green.

Assertion layers — observable semantic properties, not BLEU, not an LLM judge score:

| Layer | Question |
| --- | --- |
| Capability | Did Enigma choose the right part of the product? |
| Grounding | Were facts sourced from Enigma truth? |
| Referent | Was it talking about the right thing? |
| Constraints | Did it preserve "today", "email", "before lunch", "that one"? |
| Response meaning | Did the answer actually satisfy what Alex asked? |
| Privacy | Did only permitted information leave? |
| Authority | Could the model only do what it was allowed to do? |

```
Scenario: 15/15 active turns passed · 2 deferred
Mode: deterministic
```

Hierarchy of proof:

```
UNIT TESTS
"Does this component work?"
        ↓
C09 HARNESS
"Can Enigma's conversational architecture do this?"
        ↓
LIFE SCRIPT · DETERMINISTIC
"Can the product correctly handle this episode of a life?"
        ↓
LIFE SCRIPT · LIVE
"Can a real model reliably drive the product through this life?"
        ↓
SECURITY / RECONSTRUCTION
"Can it do so without retaining or exposing too much of that life?"
```

Alex grows as episodes, not as a biography. No `ALEX_BIOGRAPHY.md` — learn only as much as the next morning requires. **Don’t write six months of biography; write six months of ordinary events** ([demo-corpus.md](./demo-corpus.md#six-month-ordinary-life-d08f)). Timeline months live under `scenarios/alex-v1/timeline/YYYY-MM/`; Life Scripts dip into significant days. Repeated Fireworks runs of the **same** YAML are [C13](../../tickets/conversational-ui/C13-life-script-reliability.md) (reliability instrument: pass rate, referent misses, zero-tolerance security/authority/execution failures).

Week overview: `packages/evaluation/scripts/alex_jan19_week_grounding.script.yaml`. Public-effect keys: `grounded_world_response`, `tool_required`. `must_not`: `infer_unsourced_task_details`, `invent_deadline`, `invent_recommendation_strength`, `treat_context_as_calendar`. No-tool invention from `referent_candidates` must fail.

Clock jumps and world events are first-class temporal steps — the same primitive later covers SEC-06 decay and SEC-07 reconstruction across ordinary months (June 30 steal), not only `alex_week_03.yaml`. A `▶ Run Alex` UI player is next UI work; the CLI transcript is the C12 surface.

- Ticket: [C12](../../tickets/conversational-ui/C12-life-scripts.md) · next [C13](../../tickets/conversational-ui/C13-life-script-reliability.md) · corpus months [D08f](../../tickets/demo-scenario/D08f-alex-six-month.md) · later episodes [D08f-scripts](../../tickets/demo-scenario/D08f-scripts.md)
- Episodes (landed): `packages/evaluation/scripts/alex_jan19_morning.script.yaml` · `alex_conversational_sanity.script.yaml` · `alex_jan19_focus_vs_radar.script.yaml` · `alex_jan19_week_grounding.script.yaml` · `alex_jan19_assist_lifecycle.script.yaml` · `alex_jan19_speech_acts.script.yaml`
- Episodes (after monthly source events): `alex_feb12_running_late` · `alex_mar03_waiting_on_reply` · `alex_apr18_quiet_day` · `alex_may07_old_thread_returns` · `alex_jun30_what_do_you_remember`

## Conversation activity (C14)

> **Enigma shouldn't tell you that it's thinking. It should quietly show you what it's actually doing.**

Presentation is part of the product. The thread is **structured parts** (user, activity, prose, next-action/assist cards, collapsed activity) — not a flat chat log and not fake chain-of-thought.

FastAPI / Enigma remains truth, event source, orchestration, policy, and execution. The web app is a **presentation adapter**. Do not move the agent into Vercel AI SDK backend architecture.

The same Core hop has three projections:

| Mode | Surface |
| --- | --- |
| **NORMAL** | One human line (“Checked your calendar.”) |
| **CURIOUS** | Collapsed “Checked N things” ✓ list |
| **FORENSIC** | Existing under-bonnet `TurnTracePanel` + egress disclosure + Cortex |

Activity labels come from real events (`availability.checked`, `attention.queried`, …). `egress.allowed` is forensic only. Assists are factual cards (PROPOSED → APPROVED → EXECUTING → VERIFIED), not theatre.

Two concurrent streams (machine events + Enigma prose deltas) are specified; C09 is still request/response — token streaming is a C09 follow-on. v0 projects completed `llm_trace.tool_results` into the activity strip.

- Architecture: [conversational-stream.md](./conversational-stream.md)
- Decision: [ADR-027](../adr/027-streaming-presentation-adapter.md) — assistant-ui on **Vite**, not a Next rewrite
- Ticket: [C14](../../tickets/conversational-ui/C14-conversation-activity-stream.md)

## Cortex observability (C10)

The **Cortex** panel is a read-only debug view of state transitions and privacy boundaries — not LLM chain-of-thought. It is the **FORENSIC / 3D** projection of overlapping audit feeds (`EnigmaEvent`, demo evaluation log, [egress disclosures](./personal-data-security.md#egress-gate)) into [`BrainEvent`](../../apps/web/src/enigma/cortex/events.ts) pulses across stable brain regions. The in-thread activity strip ([C14](../../tickets/conversational-ui/C14-conversation-activity-stream.md)) is NORMAL/CURIOUS of the **same hops**, not a second cognition log.

**Invariant:** Cortex reads events; it never writes the world model.

- Architecture: [cortex-visualizer.md](./cortex-visualizer.md)
- UI: `apps/web/src/enigma/cortex/CortexPanel.tsx` (Three.js scene deferred)
- Privacy mode ties to the same disclosure feed as [EgressDisclosurePanel](../../apps/web/src/enigma/EgressDisclosurePanel.tsx)
- SEC-07 retention slider stub: utility vs reconstructability across SOURCE → SHADOW → FORGOTTEN ([SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md))
- Cortex shows system events, not thoughts or emotions ([ethics.md](./ethics.md))
