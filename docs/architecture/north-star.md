# North Star

**Status:** Canonical product philosophy — documentation only  
**Date:** 2026-08-17

> **Enigma turns private, messy human life into a small, actionable state machine — without trying to permanently own the life that produced it.**

This is the product thesis. Linked ADRs and architecture docs are implementations of it; they are not restated here. This page does not authorise runtime.

Enigma is starting to look less like an assistant and more like a **private OS for intent**: goals compile into permitted actions over private state. Apps are implementation details.

The bet: **privacy might not cost utility here.** Biographical detail can collapse faster than executive-function usefulness ([SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md)).

## Stack

```text
RAW EXPERIENCE  =  temporary evidence
MEANING         =  structured state
MEMORY          =  lossy, purposeful abstraction
AI              =  interprets language
POLICY          =  controls authority
RECIPES         =  encode procedure
PROTOCOLS       =  exchange minimal assertions
```

| Layer | Holds | Must not |
| --- | --- | --- |
| **Raw experience** | Mail, calendar, notes, utterances — short-lived evidence | Become the product, a second archive, or remote context |
| **Meaning** | Obligations, blockers, availability, typed transitions | Narrative biography |
| **Memory** | Consequence, not experience — inspectable, coarse, purpose-bound | Conversation logs, inner-life dossiers |
| **AI** | Language in; understands and speaks; tool calls out ([ADR-020](../adr/020-llm-conversational-boundary-not-truth.md)) | Truth, policy, memory, execution, or a second “polish” agent |
| **Policy** | What may be done, disclosed, executed ([ADR-015](../adr/015-capability-scoped-disclosure-not-data-access.md) · [ADR-019](../adr/019-delegated-authority-and-execution-ladder.md)) | Silent grant, global trust toggles |
| **Recipes** | How to pursue a goal using named capabilities ([ADR-024](../adr/024-shareable-recipes-procedure-never-personal-state.md)) | Personal state, executable code, prompt bundles |
| **Protocols** | Minimal typed assertions across Enigmas ([ADR-014](../adr/014-minimal-semantic-envelope-protocol.md)) | World-model export |

```text
raw experience  →  meaning  →  memory
                      ▲
            AI understands and speaks
            POLICY permits action
            RECIPES describe how
            PROTOCOLS assert across the boundary
```

## Seven squeezes

### 1. Private OS for intent

Goals compile into permitted actions over private state. Calendar, mail, chat, and browser are evidence sources and effectors — not the product. The user is the subject, never raw material ([ethics.md](./ethics.md) · [ADR-026](../adr/026-ethics-creed-user-is-subject.md)).

### 2. Meaningless shadow may be the canonical model

`OPEN` / `WAITING` / `BLOCKED` / … can be **privacy-friendly and product-useful**. Less biography is a better executive-function model, not a worse one ([ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md)).

### 3. Lossy personal memory class

Remember **consequence, not experience**. Tone now; later: morning meetings, 20-minute tasks, no work after 19:00. Inspectable, coarse, purpose-bound ([ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [tone-memory.md](./tone-memory.md)). Not a conversation archive. Not who you are.

### 4. Recipes ecosystem

Share **procedures, not data**. IFTTT × coping strategies × capabilities. Coaches publish without accessing the user's world ([ADR-024](../adr/024-shareable-recipes-procedure-never-personal-state.md) · [shareable-recipes.md](./shareable-recipes.md)).

### 5. Privacy as observable behaviour

Disclosure, Cortex, and minimisation are **visible** — not a wallpaper lock emoji ([privacy-model.md](./privacy-model.md) · [cortex-visualizer.md](./cortex-visualizer.md)). Inspect: what do you remember, why, forget that ([ethics.md](./ethics.md)).

### 6. Detective-Alex benchmark

Good data is **useful to Enigma and disappointing to a detective**. Curiosity is not a retention justification ([SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) · [ethics.md](./ethics.md)).

**Life Scripts** are the product acceptance test: can Alex live an ordinary fictional life through Enigma without the test needing to know how Enigma works internally? Biography exists only insofar as the next episode requires it — no `ALEX_BIOGRAPHY.md`. **Don’t write six months of biography; write six months of ordinary events** ([demo-corpus.md](./demo-corpus.md#six-month-ordinary-life-d08f) · [D08f](../../tickets/demo-scenario/D08f-alex-six-month.md)). January is the demo week, not Alex’s entire existence. Cards on radar are not the conversation subject (`objects_in_response[] ≠ conversation_focus`). Conversation state resolves language; tools establish truth — a model may not answer a private-world question from context alone. ([C12](../../tickets/conversational-ui/C12-life-scripts.md) · [C13](../../tickets/conversational-ui/C13-life-script-reliability.md) · [C09b](../../tickets/conversational-ui/C09b-discourse-focus.md) · [conversational-ui.md](./conversational-ui.md#life-scripts-c12) · [ADR-020](../adr/020-llm-conversational-boundary-not-truth.md))

### 7. Inter-Enigma

Share **answers and assertions, not state**. "Can Oscar accept Friday 21:00?" → yes. Not Oscar's calendar ([enigma-coordination-protocol.md](./enigma-coordination-protocol.md)).

## Pointers

| Squeeze | Spec |
| --- | --- |
| System map | [overview.md](./overview.md) |
| AI ≠ authority | [ADR-020](../adr/020-llm-conversational-boundary-not-truth.md) · [conversational-ui.md](./conversational-ui.md) |
| Abstract state, not biography | [ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md) · [data-retention.md](./data-retention.md) |
| Reconstructability vs utility | [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) · [demo-corpus.md](./demo-corpus.md#six-month-ordinary-life-d08f) (June 30 snapshot) |
| Recipes | [ADR-024](../adr/024-shareable-recipes-procedure-never-personal-state.md) · [shareable-recipes.md](./shareable-recipes.md) |
| Tone memory | [ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [tone-memory.md](./tone-memory.md) |
| Coordination | [enigma-coordination-protocol.md](./enigma-coordination-protocol.md) · [ADR-013](../adr/013-inter-enigma-coordination-trust-boundary.md)–[019](../adr/019-delegated-authority-and-execution-ladder.md) |
| Subject, not raw material | [ethics.md](./ethics.md) · [ADR-026](../adr/026-ethics-creed-user-is-subject.md) |
