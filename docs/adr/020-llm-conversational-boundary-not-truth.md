# ADR-020: LLM as Conversational Orchestrator, Not System Authority

**Status:** Accepted  
**Date:** 2026-08-17

> **The LLM drives Enigma; the LLM is not Enigma.**
>
> **The model understands and speaks. Enigma knows and acts.**

## Context

Conversational UI MVP (C00–C07) routes user utterances through a deterministic `intent_router` — keyword/pattern families that dispatch to typed handlers in `demo_intents.py`. C05b/c expanded phrase coverage for natural-language availability and typo tolerance. Each new utterance family required more regex surface area with diminishing returns.

C05d established **conversation context** — temporary referents (`"it"`, `"that"`, `"another"`) resolved from structured items Enigma presented, not from chat transcript invention. World state remains the only source of durable facts.

The reasoning value gate ([ADR-012](012-reasoning-value-gate-decision.md)) reached the same architectural conclusion for attention qualification: remote models may improve **semantic interpretation** and **discourse understanding**, but must not hold **authority** over policy outcomes (eligibility, ranking, presentation). Outcome **B** — semantics moved; qualification did not.

The product now pivots from expanding regex intent coverage to **LLM-driven tool calling** for conversational understanding, while preserving Enigma core as the sole authority for world truth, policy, memory, and execution.

## Decision

### Role split

| Component | Responsibility |
| --- | --- |
| **LLM** | Interpreter · conversational planner · natural language out |
| **Enigma core** | Truth · policy · memory · execution |

The LLM reads user messages, selects tools, composes responses from tool outputs, and maintains conversational coherence. It does **not** decide what is true about the user's world.

**Do not add a second, independent “personality LLM”** whose job is to make Enigma charming. Speaking is a phase of this same boundary ([C09](../../tickets/conversational-ui/C09-llm-conversational-boundary.md)), not a new trusted agent.

### What the LLM may do

- Parse natural language into tool invocations (paraphrase-invariant intent resolution)
- Plan multi-step conversational flows (query → follow-up → assist proposal)
- Generate user-facing copy from structured tool results
- Resolve discourse referents **against session context populated from prior tool outputs**

### What the LLM may NOT decide

| Domain | Authority holder |
| --- | --- |
| Obligations | Enigma obligation model |
| Availability facts | Deterministic availability / calendar projection |
| Attention qualification | Attention policy (`decide_interruption`) |
| Next-action eligibility | Next-action scorer / support layer |
| Action success | Verified execution + assist pipeline |
| World changes | Simulation / ingestion / projection |

Same lesson as the reasoning gate: **semantic/discourse yes, authority no.**

### C05–C07 handlers become tools, not language parsers

Existing deterministic handlers (`attention.get_current`, `next_action.get`, `next_action.alternatives`, `availability.check`, `world.get_changes`, `assist.propose`, `assist.approve`, etc.) are wrapped in a **tool registry**. The LLM receives JSON schemas and selects tools; handlers remain unchanged in authority and semantics.

```
USER
  ↓
CONVERSATIONAL LLM          ← one boundary, two phases
  │
  ├─ 1. INTERPRET
  │     understand utterance · resolve referent
  │     decide whether an Enigma capability is needed
  │
  ├──── ordinary conversation ──────────────┐
  │     (no private world, no action)       │
  │                                         │
  └─ 2. ACT / QUERY                         │
       tool request                         │
       ↓                                    │
   ENIGMA CORE                              │
   deterministic truth / policy             │
       ↓                                    │
   structured result                        │
       ↓                                    │
   3. RESPOND  ←────────────────────────────┘
      same model (or a smaller sibling of the
      same boundary) · no extra authority
       ↓
     USER
```

Steps 1 and 3 may be one model invocation loop, or two passes of different size. They are **not** Enigma → another AI whose job is to add adjectives.

Forbidden:

```
Enigma result  →  LLM #1 interprets  →  LLM #2 "makes it sound nice"  →  user
```

That second model can alter meaning (`urgency: LOW` → “you should probably tackle this today”). Then you must security-test and grounding-test an agent that exists to add adjectives. Not worth the goose.

Respond may speak naturally. It may **not** gain authority: no invented urgency, no upgraded recommendation, no extra tools, no unverified writes. Life Scripts already assert this (`must_not · invent_urgency`, `response_meaning`, optionality).

Ordinary conversation is a first-class lane. `"whats the colour of the sky"` must not manufacture a fake capability and must not collapse to `"Okay."`. `requires_private_world = false` → the model answers. Personal-world questions with no tool evidence still admit ignorance (`"Where did I leave my keys?"`).

No wholesale Notes, raw mail, or `PrivatePerson` crosses the remote boundary. Tool inputs and outputs are already privacy-transformed or demo-safe structured views. Tone ([ADR-025](./025-tone-memory-how-to-speak-not-who-you-are.md)) may ride with the structured result as coarse enums. **Tone transforms expression; it must not transform state, urgency, recommendation strength, or authority.**

### Conversation context (C05d) under LLM orchestration

Referents come from **tool outputs and session state**, not transcript invention:

```
WORLD STATE = durable facts (AttentionState, calendar, mail)
CONVERSATION CONTEXT = temporary referents for dialogue ("it", "another", "that")
```

When the LLM needs a referent, it calls a context-resolution tool backed by `ConversationContext` — populated when Enigma presents structured items. The LLM must not infer world facts from free-text chat history.

**Aphorisms**

- Conversation state resolves language; tools establish truth.
- Context may help the model understand the question. It may not answer the question.
- `CONVERSATION STATE` → interpretation authority; `TOOL RESULT` → factual authority.

`referent_candidates` (formerly `available_subjects`) are `{id, label, kind}` only. They exist so the model can bind “that” / “the token thing” to an id. They are not a schedule.

### Hard guardrails

1. **Personal-world question, no tool evidence → admit ignorance.** Keys, email recency, availability, obligation status — `"I don't know."` (or equivalent), never a plausible guess. **Ordinary conversation is not this case.** Sky colour, `:)` , `wait`, `what` need no Enigma capability; the interpret phase must leave that lane open. The respond phase must actually answer — a generic `"Okay."` is not understanding ([C12](../../tickets/conversational-ui/C12-life-scripts.md) frozen rule 4).
2. **No invented world facts.** Keys location, email recency, availability windows, and obligation status must trace to a tool output or fixture evidence.
3. **Assist never auto-executes.** Propose → explicit user approval → verified result (C07 invariant preserved). Conversational references may be implicit; approvals must resolve to an explicit capability object before execution. `assist.propose({})` and `assist.approve({})` may appear on the model tool request; the executed request must bind `target_id` / `proposal_id` and the LLM trace must show that fill (`referent_resolution` → `executed_tool_request`). Queries can stay implicit. Authority transitions cannot. Named lexical help must not blindly execute `current_subject` when the utterance names a different referent.
4. **Silence stays silence.** Proactive silence is a presentation/event-log primitive, not an LLM-generated chat turn ([conversational-ui.md](../architecture/conversational-ui.md)).

5. **Jan 19 regression preserved.** At `cp-2026-01-19T10:00`, token-audit stays in `context` with next-action support — never promoted to `needs_you` by conversational routing.
6. **Respond does not gain authority.** Copy from structured results may be natural. It may not invent urgency, upgrade optionality into obligation, widen scope, or execute. A second “make it nice” model is forbidden.
7. **Conversation state is not world truth.** A model may not answer a question about the user's private world from conversational context alone. It must ground the answer through an Enigma capability. **Conversation state resolves language; tools establish truth.** Context may help the model understand the question. It may not answer the question. `CONVERSATION STATE` → interpretation authority; `TOOL RESULT` → factual authority. `referent_candidates` (`{id, label, kind}`) are for referent resolution only — not timing, urgency, details, status, recommendations, or world claims.
8. **Yes inherits the speech act. It never upgrades it.** SHOW? → yes → SHOW. EXPLAIN? → yes → EXPLAIN. APPROVE THIS ACTION? → yes → APPROVE. Never SHOW? → yes → `assist.approve`. Approval is authorized only when the previous Enigma turn created an **explicit approval affordance** (the Assist proposal card). The guard lives in Enigma core — reject `assist.approve` when `pending_dialogue_act` is not `APPROVE_CONFIRMATION`. Do not teach `intent_router` the word “yes”.
9. **A conversational correction may change what Enigma is talking about; it may never by itself authorize Enigma to do something.** Resolving a referent is not an action. SUBJECT SELECTION ≠ CAPABILITY SELECTION. `assist.propose` is PREPARE, not the answer to a clarifying question.
10. **The model may possess general knowledge. It may not manufacture current-world evidence.** Specific external claims (venues, addresses, prices) require external evidence just as specific personal claims require world-model evidence.

### Five lanes

Referent resolution sits under all five. It is not itself an action.

| Lane | Example | Authority |
| --- | --- | --- |
| **1. CONVERSATION** | `yeah :)` · `wait` | Model speaks. No Enigma capability. |
| **2. GENERAL KNOWLEDGE** | `how do design tokens work?` · `what is sushi?` · `yes but how` | Model may use generic knowledge. No private-world facts. No tools required. |
| **3. PRIVATE-WORLD QUERY** | Saturday plans · what's on this week | Enigma capability (`agenda.get`, `attention.get_current`, …). Conversation state may not answer. |
| **4. EXTERNAL-WORLD QUERY** | sushi places in Shoreditch? | Search capability required. **Must not invent venues, addresses, or prices.** If the capability is not on v1, defer honestly — do not fake a restaurant table. |
| **5. ACTION** | book one | `assist.propose` → explicit approval → verified write. |

Speech acts — UNDERSTAND / ADVISE / PREPARE / ACT / INSPECT / APPROVE — cannot all collapse into `assist.propose`. Inspect and advise that are not on v1 must defer, not cheat via PREPARE.

**Turn-local constraints** follow the same philosophy as turn-local tone ([ADR-025](./025-tone-memory-how-to-speak-not-who-you-are.md)): “we will be in Shoreditch” is `{location=Shoreditch, applies_to=Saturday brunch}` for this session. It evaporates. It is not “Alex lives in Shoreditch,” not durable user memory, and not an action.

**Assist store vs conversation:** a proposal that is surfaced must store its id authoritatively; conversation context must reference that same id; approval must resolve that same id. There is no visible/approvable proposal whose execution cannot retrieve it.

Life Script: `packages/evaluation/scripts/alex_jan19_speech_acts.script.yaml`.

### intent_router retained as fallback / test oracle

`intent_router.py` and regex phrase families are **frozen**. No new phrase families in C05b/c. They remain:

- Fallback path when LLM is disabled or unavailable
- Deterministic test oracle for Alex benchmark paraphrase-invariance checks
- Regression baseline for tool-calling parity

Implementation: [C09](../../tickets/conversational-ui/C09-llm-conversational-boundary.md).

## Consequences

- C05b/c regex expansion stops; C09 supersedes language parsing.
- C05e (recent source queries) may ship as a tool before or alongside C09 orchestrator wiring.
- Alex benchmark gains an LLM conversational slice: paraphrase invariance, referent retention, Jan 19 truth fidelity, keys→don't know.
- Phrase-map / IntentOracleLLM coverage (the C09 harness) is a **test oracle**, not proof that a remote model can plan tools. Phrase maps are scaffolding around the model. Off-script paraphrases live in `test_c09_llm_paraphrase_invariance.py`. Live proof is **Fireworks via `AuditedEgressGate`** (same production egress path as reasoning): skip unless `ENIGMA_C09_LIVE=1` and `FIREWORKS_API_KEY`; 3–5 reps; assert tool name + arguments + subject ID. Graduation: a real model passes that off-script chain while every factual answer and action stays grounded in Enigma tools. Live Demo conversation uses the C09 orchestrator when a provider is configured (Fireworks preferred). `intent_router` remains the fallback when LLM is explicitly disabled or no provider key is available.
- Remote inference remains disable-able; deterministic fallback must still satisfy Alex milestone.
- Future Live mode (C08) shares the same tool registry boundary — only transport and privacy gating differ.
- Agents must not let the LLM short-circuit attention qualification, availability checks, or assist approval.
- **No polish LLM.** Interpret and respond are phases of C09. A second model that "makes it sound nice" is a new authority surface. If two model sizes are used, they remain one conversational boundary.
- Shareable recipes ([ADR-024](./024-shareable-recipes-procedure-never-personal-state.md)) extend this split: the LLM may match a goal to a recipe id; it must not invent steps, pick join URLs, execute, or treat the recipe as a prompt bundle. Recipe runtime waits on C09 LLM proof and SEC-05 — not a C09 scope expansion.
- Tone memory ([ADR-025](./025-tone-memory-how-to-speak-not-who-you-are.md)) extends the same split for *register*: after C09 proof, the orchestrator may receive a small REMOTE_SAFE style-enum profile with `current_subject` and tool results — **not** the last 200 messages. The LLM may use the profile to choose wording; it must not write a personality dossier, retain conversation logs as style evidence, or treat a frustrated turn as “user is irritable.” **Tone may transform expression; it may not transform state, urgency, recommendation strength, or authority.** Tone runtime waits on C09 LLM proof — not a C09 scope expansion.

## Related

- [north-star.md](../architecture/north-star.md) — AI interprets language; Enigma holds truth, policy, memory, execution
- [ADR-012 — Reasoning value gate](012-reasoning-value-gate-decision.md)
- [ADR-010 — NextAction ≠ AttentionItem](010-next-action-not-attention.md)
- [ADR-019 — Delegated authority ladder](019-delegated-authority-and-execution-ladder.md)
- [ADR-024 — Shareable recipes](024-shareable-recipes-procedure-never-personal-state.md) · [shareable-recipes.md](../architecture/shareable-recipes.md)
- [ADR-025 — Tone memory](025-tone-memory-how-to-speak-not-who-you-are.md) · [tone-memory.md](../architecture/tone-memory.md) · [C11](../../tickets/conversational-ui/C11-tone-memory.md) (`future`)
- [conversational-ui.md](../architecture/conversational-ui.md)
- [C05d — Conversation continuity](../../tickets/conversational-ui/C05d-conversation-continuity.md)
- [C09 — LLM conversational boundary](../../tickets/conversational-ui/C09-llm-conversational-boundary.md)
- [C12 — Life Scripts](../../tickets/conversational-ui/C12-life-scripts.md) — tests interpret *and* respond (`response_meaning`)
