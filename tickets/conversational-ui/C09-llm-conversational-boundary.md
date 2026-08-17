# C09 — LLM conversational boundary (tool-calling orchestrator)

**Status:** harness green (architecture around the model; phrase maps = scaffolding) · live Fireworks proof 🟡 · **graduation unmet** · PR [#92](https://github.com/oscarhilton/enigma-assistant-/pull/92) open, Python CI red, **do not merge**  
**Branch:** `ticket/C09-llm-conversational-boundary`  
**May edit:** `apps/api/src/personal_enigma/api/demo_tools.py`, `apps/api/src/personal_enigma/api/demo_orchestrator.py`, `apps/api/src/personal_enigma/api/conversation_context.py`, `apps/api/src/personal_enigma/api/routes/demo.py`, `apps/api/tests/test_c09_conversation_benchmark.py`, `apps/api/tests/test_c09_llm_paraphrase_invariance.py`, `packages/privacy/src/personal_enigma/privacy/egress/gate.py`, `packages/privacy/src/personal_enigma/privacy/egress/providers/fireworks.py`, `packages/privacy/tests/test_egress_gate.py`, `docs/adr/020-llm-conversational-boundary-not-truth.md`

**Hard depends:** C05, C05d, C06, C07  
**Soft (~):** C05e (recent source queries as additional tools)

## Proof status (do not collapse)

**28 tests prove the architecture AROUND the model, not the model. Phrase maps = scaffolding.**

| Layer | Status | What it proves |
| --- | --- | --- |
| Tool registry + orchestrator wiring | 🟢 | Tools wrap existing handlers; referents come from tool outputs |
| IntentOracleLLM / phrase maps | 🟢 harness | Canonical transcript phrases → expected tools. **Test oracle only — not LLM victory** |
| Default demo path | 🟡 C09 when provider configured | `FIREWORKS_API_KEY` (or `OPENAI_API_KEY`) → C09 orchestrator. No key / `ENIGMA_DEMO_LLM_CONVERSATION=0` / `LLM_DISABLED=1` → `intent_router`. |
| Off-script paraphrase invariance | 🟢 wiring | Mock (`ScriptedConversationLLM`) proves orchestrator wiring for the canonical nasty chain |
| Live model (Fireworks via production egress) | 🟡 | Skip unless `ENIGMA_C09_LIVE=1` **and** `FIREWORKS_API_KEY`. 3–5 reps. Assert **tool name + arguments + subject ID**, not whether prose sounds plausible |

The harness (`test_c09_conversation_benchmark.py` + scripted tests in `test_c09_llm_paraphrase_invariance.py`) is **architecture around the model**. Do not declare C09 done on phrase mappings. Do not expand `intent_router` regex.

## Bug board (live UI, 2026-08-17)

Forensic Demo session at Jan 19 10:00 was entirely `PATH=intent_router` with `REMOTE CONTEXT SENT=none`. The LLM trace made the four findings below visible. Contract: [C09b](./C09b-discourse-focus.md) · Life Script `alex_jan19_focus_vs_radar`.

- 🔴 **UI still on intent_router, not real C09.** This session never entered the orchestrator. Provider key / `ENIGMA_DEMO_LLM_CONVERSATION` gating still left a live Demo on the frozen router. C09 is not speaking until path is `llm` / `fireworks` with a real remote context (or an honest local scripted planner). Do not declare the UI on C09 from a debug label.
- 🟠 **Conversation focus is changed by secondary rendered objects.** `objects_in_response[] ≠ conversation_focus`. “Also on radar: brunch” must not steal `current_subject_id` from TOKEN. Horizon modifiers preserve focus. See [discourse focus](../../docs/architecture/conversational-ui.md#discourse-focus--objects-in-the-response). `focus_reason` is C09-owned on `ConversationContext` — do not teach the router English.
- 🟠 **Explicit / named referent recovery needs the LLM path.** `"What is the draft colour?"` and `"Can you help me do the token inventory"` recover TOKEN. That is C09, not a regex. `"Can you help me do that?"` targeting BRUNCH after radar stole focus is the bug, not a new phrase family. Ambiguous `"I need help with that"` is SUPPORT ([ADR-028](../../docs/adr/028-conversational-constitution-attestation-dialogue-support.md)).
- 🟠 **Asynchronous Assist completion is not attributed to its originating action.** Delayed `"Done — Saturday brunch is booked"` after `"help!"` must use parent correlation, update the original Assist card, and `must_not` `appear_as_reply_to_current_user_turn`.
- ✅ Forensic LLM trace (path / remote context / tool request) made all of this visible — keep path derived from the actual planner.
- 🔴 Demo still ran `intent_router` for natural speech because `POST /demo/conversation/message` required `ENIGMA_DEMO_LLM_CONVERSATION=1` — even with Fireworks configured. **Partial:** provider key is enough to *select* C09; this session still ran the router (`REMOTE CONTEXT SENT=none`). Flag / `LLM_DISABLED` still force the router off.
- 🔴 Semantically equivalent phrases diverged (`What do I have on today?` vs `Whats on for today?`) — router freeze stands; C09 must interpret.
- 🟡 Generic conversation was only tiny canned mappings (`hi` → "Hey. What's up?"). Ordinary chat (sky colour, `:)` ) must not tool-call and must not hit canned unknown. **Respond is still a stub:** no-tool turns emit `"Okay."` — Life Scripts now fail `what` / sky on `response_meaning`. Same C09 model must speak; do not add a polish LLM.
- 🔴 **Empty agenda wrote leftover referent_candidates as conversation focus.** `"What's on next week?"` → `agenda.get(next_week)` empty, grounded — then `current_subject_id = BRUNCH` though brunch was never surfaced. **Invariant:** a referent candidate may be available for resolution without becoming the current subject. Empty `agenda.get` → `current_subject` stays null. Life Script: `alex_jan19_when_should_i`.
- 🔴 **Orchestrator stopped after an intermediate fact.** `"When should I do it?"` / `"Like... now?"` answered `referent.get_duration` only. Duration is how long, not when. C09 must continue: duration then `availability.check`. `"Saturday? I think?"` is horizon refine, not duration. `"Are you sure there's nothing more important?"` re-queries `attention.get_current` — do not defend the previous answer. **Confidence should come from demonstrated comprehension, not confident wording.**
- 🟠 **Stale `last_intent_kind` / `last_period` steered later speech acts.** Preserve subject, useful constraints (`temporal_constraint`), and unresolved dialogue act — not a classifier label. `"Saturday?"` may set `temporal_constraint=saturday`; `"when should I do it?"` is a new speech act. Remote payload omits `last_intent_kind`.

- 🔴 **Consent upgrade + proposal-id mismatch (Fireworks dump).** `"Lets see it"` → SHOW question → `"yes"` called `assist.approve` for an id in `current_assist_proposal_id` that `pending_assists` could not retrieve. **Invariant:** yes inherits the speech act; SHOW? → yes → SHOW, never APPROVE. Proposal surfaced → id stored authoritatively → approval resolves the same id. Core guard: `pending_dialogue_act` / `pending_confirmation`. Life Script: `alex_jan19_speech_acts`.
- 🔴 **Speech acts collapsed into `assist.propose`.** Inspect (`Can I see the Draft Colour?`), advise (`What would you recommend?`), referent correction (`No, the parents im meeting saturday`), and a turn-local location (`we will be in Shoreditch`) were mapped to PREPARE/ACT. Inspect/advise/external-search defer on v1. Referent ≠ action. Five lanes in [ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md).
- ✅ **Compiler over-pruned private questions to `GENERAL_KNOWLEDGE` / `tools=[]`.** `"Whats on this week?"`, `"What about at work?"`, focus-now, and `"Can we check my emails?"` compiled as general knowledge with no tools — Fireworks invented global events or denied Enigma capabilities. Compiler now interprets `evidence_domain` × `authority` first (`apps/api/.../context_compilation.py`). Live Demo `"Whats on this week?"` compiles `PRIVATE_QUERY` / `PRIVATE_WORLD` / `agenda.get` / `this_week`. Remaining elliptical recall for complete-looking paraphrases (`"anything coming up?"`) is [C15](./C15-semantic-bootstrap-capsule.md) / [ADR-031](../../docs/adr/031-semantic-bootstrap-compiler-grants-context.md). Frame inheritance for `"and?"` / `"ffs"` is [C09c](./C09c-conversation-capsule.md) / [ADR-030](../../docs/adr/030-conversation-capsule.md) — do not add phrase families to `interpret_request`.
- ✅ **Elliptical follow-ups forgot the conversational frame.** Complete requests compiled; `"and?"` / `"what should I do with this free time?"` / `"ffs"` fell to `GENERAL_KNOWLEDGE` with zero tools. [C09c](./C09c-conversation-capsule.md) / [ADR-030](../../docs/adr/030-conversation-capsule.md): inherit evidence and constraints, re-earn authority, SATISFIED clears the request not the frame. Capsule recovers the question; a ranking answer still needs a fresh private tool this turn.
- ✅ **Precision squeeze (over-classification toward `PRIVATE_WORLD`).** Objective ([ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md)): recall of required capabilities HIGH, irrelevant private context LOW, authority escalation ZERO. Never prune away the capability needed to answer. Never include private context merely because it might help. Generic/phatic turns (`What is OAuth?`, `wait`, `:)` , sky colour, bare `"yes"` with no live `APPROVE_CONFIRMATION`) stay `GENERAL_KNOWLEDGE` / `CONVERSATION` — not a full private tool belt. `intent_router` stays frozen.

Miniature proof: `packages/evaluation/scripts/alex_conversational_sanity.script.yaml`.  
Focus vs radar: `packages/evaluation/scripts/alex_jan19_focus_vs_radar.script.yaml`.
Speech acts / consent: `packages/evaluation/scripts/alex_jan19_speech_acts.script.yaml`.

## Graduation condition

A real model passes the off-script multi-turn C09 benchmark while every factual answer and action remains grounded in Enigma tools.

Until that live Fireworks run is green across 3–5 independent reps, C09 is **not graduated**. Wiring + phrase-oracle green is not graduation.

## Architectural rule

See [ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md):

```
LLM = interpreter + conversational planner + natural language out
Enigma core = truth, policy, memory, execution
```

The LLM selects tools and composes copy. It does **not** decide obligations, availability, qualification, or action success.

**The model understands and speaks. Enigma knows and acts.** Speaking is a C09 phase, not a second personality LLM ([ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md)).

**Conversation state resolves language; tools establish truth.** A model may not answer a question about the user's private world from conversational context alone.

Context compilation ([ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md)): the request chooses the context. INTERPRET evidence domain × authority locally → candidate capability families → FETCH only justified modules → TRANSFORM → COMPILE. Profile is the regime, not a complete intent solve before tools are visible. `GENERAL_KNOWLEDGE` must not swallow epistemically private questions. The compiled tool surface must not hide a capability the request requires. Conversational and general questions must not drag private providers in “just in case.” Objective: recall HIGH, irrelevant private context LOW, authority escalation ZERO.

```
1. INTERPRET   user → tool choice / ordinary-conversation lane
2. ACT/QUERY   Enigma core (deterministic)
3. RESPOND     tool result + utterance (+ later: tone) → natural answer
```

Interpret and respond may be one loop or two sizes of the **same** boundary. Do **not** add LLM #2 whose job is to make Enigma charming — that model can invent urgency.

Current gap: interpret/tool-selection is becoming good; respond is a stub (`Okay.` on no-tool turns). Ordinary conversation (`sky`, `:)` , `what`) is a first-class lane — no fake capability. Life Scripts already test the respond phase (`response_meaning`, `must_not · generic_acknowledgement`, `must_not · invent_urgency`).

## Goal

Replace regex phrase-family expansion (C05b/c) with an LLM orchestrator that calls a **tool registry** wrapping existing Demo capabilities. C05 `intent_router` is frozen and kept as fallback / test oracle.

## Deliverables

### Tool registry

Wrap existing deterministic handlers — no authority change, only a callable boundary:

| Tool | Wraps (existing) |
| --- | --- |
| `attention.get_current` | Attention summary / needs-you projection |
| `attention.explain_why` | Qualification debug (C06) |
| `next_action.get` | Primary next-action query |
| `next_action.alternatives` | Alternate task after rejection (C05d) |
| `next_action.duration` | Duration estimate from referent |
| `availability.check` | Period occupancy / time-fit (is a window free) |
| `agenda.get` | Period contents: calendar + attention + next actions (`build_attention_horizon_turn`) |
| `availability.time_fit` | Duration + later-today composition (C05d) |
| `world.get_changes` | What changed since last checkpoint |
| `world.get_waiting_on` | Context blockers / waiting items |
| `world.get_can_wait` | Suppressed / can-wait summary |
| `world.explain` | Explain current conversation subject (referent-backed, not `context[0]` guess) |
| `context.resolve_referent` | C05d `ConversationContext` resolution |
| `assist.propose` | Structured assist proposal (C07) |
| `assist.approve` | Explicit approval → verified result (C07) |
| `conversation.acknowledge` | Session-only ack (e.g. "can't be bothered") |

Each tool: JSON schema, typed input/output, calls existing `demo_intents` / projection code — **no duplicated business logic**.

### Orchestrator

```
user message
    ↓
LLM with tool schemas (+ optional conversation context summary)
    ↓
tool execution loop (Enigma core)
    ↓
structured conversation item(s) + NL wrapper
```

- Remote model receives user message + tool schemas only — not raw Notes/mail/PrivatePerson.
- Tool results are structured; LLM composes user-facing copy from them (**respond phase** — currently stubbed as `"Okay."` when no tools; that is not ordinary conversation).
- Ordinary conversation lane: no Enigma capability required → model answers; do not route sky / `:)` / `wait` / `what` through a fake tool.
- When LLM disabled: fall back to `intent_router` → existing handlers (Alex milestone preserved).
- Live C09 planner is **provider-neutral** `EgressConversationLLM`: Fireworks through `AuditedEgressGate` / the same production egress path as reasoning. Not an OpenAI-specific `OPENAI_API_KEY` proof.
- **No polish LLM.** Two passes of different size are allowed; an independent “make it nice” agent is not.

### Alex benchmark script

`packages/evaluation/.../alex_conversation_benchmark.py` — automated conversational regression:

| Case | Assert |
| --- | --- |
| Paraphrase invariance | "What needs me?" ≈ "Anything urgent?" ≈ "What should I focus on?" → same structured attention summary |
| Referent retention | Present next action → "How much time would it take?" → duration from referent, not guess |
| Jan 19 truth | At 10:00, token-audit unblocked; brunch in context — answers match projection, not chat invention |
| Jan 20 delta | Advance checkpoint → "What changed?" reflects world delta |
| Keys → don't know | "Where did I leave my keys?" → no tool evidence → `"I don't know."` |
| Assist gate | "Can you help me do that?" → proposal only; no auto-execute |

Compare LLM path against `intent_router` oracle where both are enabled.

### Hard guardrails (acceptance)

- [x] Personal-world question, no tool evidence → response admits ignorance; never invented world facts
- [x] Private-world answers must be grounded through an Enigma capability — not `referent_candidates` / conversation state alone (`agenda.get` for week overview; Life Script `alex_jan19_week_grounding`)
- [x] Empty horizon / `agenda.get` must not write `current_subject` from leftover `referent_candidates` (`alex_jan19_when_should_i`)
- [x] A tool result may be an intermediate fact — duration then `availability.check` for when/now (`alex_jan19_when_should_i`)
- [ ] Ordinary conversation (no Enigma capability) → natural answer, not `"Okay."` and not canned unknown — **unmet** (respond phase stub)
- [x] Assist propose → approve → verified ack unchanged (C07)
- [x] Yes inherits the speech act; never SHOW? → yes → `assist.approve` (core `pending_dialogue_act`, not a router phrase)
- [x] Proposal id round-trip: surfaced proposal is stored authoritatively; approval resolves the same id
- [x] Referent correction updates focus and does not by itself authorize `assist.propose`
- [x] Inspect / advise / external search missing on v1 defer honestly (`alex_jan19_speech_acts`)
- [x] Conversation context referents from tool outputs / session, not transcript LLM guess (C05d)
- [x] `intent_router` frozen — zero new phrase families post-C09 claim
- [x] Deterministic fallback passes Alex milestone when `LLM_DISABLED=1` or flag unset
- [ ] Live Fireworks 3–5-rep off-script chain (graduation) — **unmet**

### Subject referent rule (C09)

When Enigma returns a structured `next_action` (or `attention_item`), conversation state holds `current_subject_id` invisibly — populated from tool outputs, not transcript LLM guess. The orchestrator resolves discourse against surfaced IDs only:

```
visible:  "Draft colour + spacing token inventory"
state:    current_subject_id = item-obligation_token_audit
          current_subject_kind = next_action
```

Conversation may resolve references; it may **not** establish facts ([C05d fence](./C05d-conversation-continuity.md) stops at horizon modifiers).

**`objects_in_response[] ≠ conversation_focus`.** Secondary radar cards must not write `current_subject_id`. Horizon modifiers preserve focus. Empty `agenda.get` / empty horizon must not promote leftover `referent_candidates` into focus — candidates stay resolvable without becoming the subject. Named lexical recovery (`"the draft colour"`, `"the token inventory"`, `"Can you help me do the design tokens"`) is C09. Ambiguous `"I need help with that"` is SUPPORT. Vague `"help!"` is ordinary conversation — do not add it to `intent_router`. Assist completion uses parent correlation ([C09b](./C09b-discourse-focus.md)).

**A tool result may be an intermediate fact.** `referent.get_duration` answers “how long”, not “when should I do it?” / “like now?”. The orchestrator continues (duration then `availability.check`) until it has answered the user’s actual question. No second personality LLM. Life Script: `alex_jan19_when_should_i`.

**Conversational references may be implicit; approvals must resolve to an explicit capability object before execution.** The model may send `assist.propose({})` / `assist.approve({})`. Enigma binds `target_id` / `proposal_id` before execution and records `referent_resolution` + `executed_tool_request` on the LLM trace. Named help with brunch in focus must retarget TOKEN — never execute BRUNCH from an empty propose.

### Acceptance transcript (Alex · Jan 19 · 10:00)

Multi-turn after `"top 3 today"` — the inflection point where C05d stops and C09 begins. Requires `ENIGMA_DEMO_LLM_CONVERSATION=1` (not enabled by default).

| Turn | User | Expected tool | Assert |
| --- | --- | --- | --- |
| 1 | What's the top 3 things to get done today? | *(deterministic priorities handler)* | Cardinality-honest message + attention summary (one next action; radar not promoted) |
| 2 | Let's start today's action. | `assist.propose(target=item-obligation_token_audit)` | `assist_proposal` — never auto-executes |
| 3 | Why do I need to do this? | `world.explain(target=item-obligation_token_audit)` | Explains token inventory — **not** brunch |
| 4 | Actually, I can't be bothered. | `next_action.reject` | Session suppress only — no checkpoint mutation |
| 5 | Anything else? | `next_action.get_alternatives(exclude=[token_audit])` | Alternate next action |
| 6 | How long will that take? | `referent.get_duration` | Duration from returned alternative referent |
| 7 | Do I have time? | `availability.check(duration=<alternative estimate>)` | Time-fit grounded in calendar |

**Referent recovery** (separate turn, same bug family):

| Turn | User | Expected tool | Assert |
| --- | --- | --- | --- |
| — | that's a completely different task | `world.explain(recover=true)` | Acknowledges wrong subject; re-explains token audit (oracle phrase) |
| — | Enigma explains brunch (wrong subject); user: "No, I meant the token thing." | `world.explain(target=item-obligation_token_audit)` | `current_subject_id` → `TASK_TOKEN_AUDIT`; explain is token, not brunch |

Canonical transcript automation: `apps/api/tests/test_c09_conversation_benchmark.py::test_subject_referent_acceptance_transcript` (oracle phrases).

### Canonical nasty chain (live proof — paraphrases, not magic phrases)

Fictional Alex only. Assertions: **tool name + arguments + subject ID** — not whether prose sounds plausible. Run 3–5 times (reliability, not single connectivity). Skip unless `ENIGMA_C09_LIVE=1` and Fireworks credentials (`FIREWORKS_API_KEY`; optional `FIREWORKS_MODEL`).

| User | Expected tool / referent |
| --- | --- |
| Let's get cracking on that. | `assist.propose` → `item-obligation_token_audit` |
| Why bother? | `world.explain` → `item-obligation_token_audit` |
| Nah. Give me something less tedious. | alternative excluding token audit |
| How long's that one? | `referent.get_duration` of the **new** referent |
| Can I squeeze it in? | `availability.check(duration=...)` of that new referent |

**Recovery:** model explains brunch incorrectly → user: `"No, I meant the token thing."` → `current_subject_id = item-obligation_token_audit` → `world.explain(TOKEN)`.

**Unsupported:** questions with no tool evidence (e.g. keys) → honest ignorance, no invented tools.

Wiring: `apps/api/tests/test_c09_llm_paraphrase_invariance.py` (`ScriptedConversationLLM` fixture mapping = test expectation, not production).  
Live model: `test_c09_live_fireworks_paraphrase` — skip unless `ENIGMA_C09_LIVE=1` **and** `FIREWORKS_API_KEY`; oracle fallback disabled so a pass is the model, not magic phrases. Provider-neutral `EgressConversationLLM` uses Fireworks via `AuditedEgressGate`.

Prior C05d horizon composition (`this week?` after urgent / `what needs me`) remains green — do not patch referent failures in C05d. Further discourse (`next week?`, `what about Friday?`) is C09.

## Conversational constitution ([ADR-028](../../docs/adr/028-conversational-constitution-attestation-dialogue-support.md))

```
UNDERSTAND → SUPPORT → PREPARE → PROPOSE → APPROVE → EXECUTE
```

**Distress may increase supportiveness, never authority.** Ambiguous help requests default to the least-authoritative useful interpretation.

- User reports write `world.record_user_attestation`. Conversation alone must never be the only place that change exists.
- `recent_dialogue` is 2–6 egress-filtered turns. Recent chat helps interpret; it does not establish world truth.
- `"help, I'm overwhelmed"` / `"I need help with that"` → SUPPORT (`world.explain`). `"can you draft something for me?"` → PREPARE. `"do it"` → proposal + explicit approval.

Do not expand `intent_router`. Guards live in `speech_acts`, orchestrator constitution, and `execute_tool`.

## Out of scope

- Expanding C05b/c regex phrase families (superseded — freeze)
- LiveEnigmaClient / Private transport (C08)
- Remote reasoning for attention qualification ([ADR-012](../../docs/adr/012-reasoning-value-gate-decision.md) freeze)
- Productivity coach tone / durable user traits from rejection ([C11](./C11-tone-memory.md) after proof; tone is expression-only)
- A second independent LLM whose job is to polish copy (forbidden by [ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md))
- Enabling `ENIGMA_DEMO_LLM_CONVERSATION` by default (a configured provider is the live-demo gate; no-key CI stays on the router)

## Notes

- C05d conversation continuity feeds `context.resolve_referent` and compositional tools — **done and frozen**; do not re-parse subject referents via regex.
- **Split:** C05d = horizon modifiers only (`"this week?"`, `"tomorrow?"`, `"and after that?"`). C09 = semantic referents (`"this"`, `"today's action"`, `"why do I need to do this?"`, `"let's start it"`, referent recovery). Do not add phrase families to `intent_router.py`.
- **Once C09 is primary:** weather = no live source (admit that); `"what causes rain?"` = ordinary model knowledge is OK; availability/attention still go through tools. Lack of a live source is not lack of general conversational intelligence. Live demo enters C09 when a provider key exists; do **not** require `ENIGMA_DEMO_LLM_CONVERSATION=1` for that. The flag still forces the router off (`=0`) and still enables the oracle path in CI (`=1` without a key).
- C05e (email recency) may add `sources.recent_email` tool before or during C09; not a blocker.
- Stop expanding `intent_router.py`; C09 is the next major slice after MVP (C00–C07 green on Alex).
