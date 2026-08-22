# North Star

**Status:** Canonical product philosophy — documentation only  
**Date:** 2026-08-17

> **Enigma turns private, messy human life into a small, actionable state machine — without trying to permanently own the life that produced it.**

This is the product thesis. Linked ADRs and architecture docs are implementations of it; they are not restated here. This page does not authorise runtime.

Enigma is starting to look less like an assistant and more like a **private OS for intent**: goals compile into permitted actions over private state. Apps are implementation details.

The bet: **privacy might not cost utility here.** Biographical detail can collapse faster than executive-function usefulness ([SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md)).

Constitutional corollary (does not replace the thesis above):

> **Enigma should reduce the work required to live a life without reducing the person’s authorship of it.**

Product / experiential North Star — evaluate product decisions against this; it does not add entities:

> **Make safe agency feel obvious, bounded, and delightful.**

| Word | Means |
| --- | --- |
| **Safe** | Privacy, epistemics, and authority doing real work |
| **Agency** | Notices, fetches, prepares, waits, acts when permitted, verifies |
| **Obvious** | Understandable without an architecture diagram |
| **Bounded** | See accessed / currently held / left device / retained / dropped |
| **Delightful** | Not a GDPR console — THE Goose with translucent cargo |

Human version: a navigator beside you (Polaris), with access to an extremely safe hidden machine (Enigma) and a deeply enthusiastic goose. The navigator doesn't know everything. The goose doesn't understand everything. The machine can't do whatever it wants. The Vault doesn't gossip. The Council advises; none of them decides your life.

Visibility (stop the theme park — sitcom brief historically in `product-characters.md` at `13ed0d3`, not restored on `main`; Council is an **advisory projection**, not a new cast of star-named characters — [council.md](./council.md) · [NORTHSTAR-SEARCH-DOCS](../../tickets/northstar/NORTHSTAR-SEARCH-DOCS.md)):

| Layer | Who / what |
| --- | --- |
| Always visible / intuitive | You, Polaris (navigator), THE Goose, Cases |
| Inspectable when relevant | Council (specialist lenses), Vault / Memory, Foundry / Machine, Harbour (readiness), Sources |
| Hidden substrate | Enigma (canonical world model — not a speaking character) |
| Forensic / advanced | Cortex, Lens, Observatory (programme truth), EvidenceBundle, lineage, egress, authority, epistemic status |

The user should never need to learn the architecture to benefit from it. Architecture is there when they become curious. Shadows, satchel, cargo, Workbench, Engine Room stay **internal / inspectable metaphors**, not a front-page cast. Council **seats** are inspectable lenses, not extra nouns on the home screen. Do not put Aldebaran/Spica/Canopus on the always-visible layer.

Conversational Assistant remains the language boundary ([ADR-020](../adr/020-llm-conversational-boundary-not-truth.md)); it is not a second chair and not Enigma.

Next strategic frontiers (orthogonal; none authorise runtime here):

- **Programme truth (engineering)** — Observatory first: what exists / is wired / tested / running / usable, with derived evidence, not a typed-in percent ([observatory.md](./observatory.md)).
- **The relationship** (relational bootstrap: product taste + explicit preferences + shared motifs + current register). Humour constitution is historical ADR-038 — file not on `main`; see [NORTHSTAR-SEARCH-DOCS](../../tickets/northstar/NORTHSTAR-SEARCH-DOCS.md).
- **Local choice under search** — later than Observatory 01–02. Polaris receding-horizon planning over a compiled life position, never a universal life score ([polaris-search.md](./polaris-search.md) · [council.md](./council.md) · [ADR-044](../adr/044-receding-horizon-action-search.md)).
- **Activity readiness** — Harbour: CAN they begin, and what stands between wanting and starting? PolarIS still decides whether now is a good move ([harbour.md](./harbour.md)). No star name. Not a tyrant.

Do not implement those runtimes from this page.

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
| **Memory** | Consequence, not experience — inspectable, coarse, purpose-bound | Conversation logs, inner-life dossiers, six months of prompts |
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

### 8. Local choice, not life optimisation

Enigma does not optimise a person's life. Polaris may **search** locally available futures and recommend the next bounded move; the Council may **read** specialist factors over that position; Harbour may compile **readiness** (transition friction) without becoming a productivity tyrant. None may commit a principal variation, invent a universal life score, govern the user, or skip READ / PREVIEW / PREPARE / COMMIT ([polaris-search.md](./polaris-search.md) · [council.md](./council.md) · [harbour.md](./harbour.md) · [ADR-044](../adr/044-receding-horizon-action-search.md) · [ADR-046](../adr/046-local-evaluation-under-uncertainty.md)).

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
| Safe agency / visibility | Visibility table on this page (historical `product-characters.md` / ADR-038 / C33 not on `main` — [NORTHSTAR-SEARCH-DOCS](../../tickets/northstar/NORTHSTAR-SEARCH-DOCS.md)) |
| Local choice / search | [polaris-search.md](./polaris-search.md) · [council.md](./council.md) · [ADR-044](../adr/044-receding-horizon-action-search.md)–[048](../adr/048-structured-search-trace-and-lens.md) |
| Programme truth | [observatory.md](./observatory.md) (engineering; not a Council seat) |
| Activity readiness | [harbour.md](./harbour.md) (CAN begin; not a planner, not a star) |
