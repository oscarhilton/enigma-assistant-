# ADR-024: Shareable recipes — procedure, never personal state

**Status:** Accepted  
**Date:** 2026-08-17

> **Recipes contain procedure, never personal state.**
>
> A recipe is a **declarative procedure**, not executable code and not a prompt bundle.

## Context

Enigma already separates **world truth** (private model, attention, obligations) from **conversational interpretation** ([ADR-020](./020-llm-conversational-boundary-not-truth.md)) and **execution authority** ([ADR-019](./019-delegated-authority-and-execution-ladder.md)). What it does not yet name is a third reusable object: an **executive-function pattern** that many people share, but that each person binds to *their* calendar, links, and permissions.

Hardcoding those patterns into product (a built-in “join ADHD call” button, a baked Zoom URL, a phrase family in `intent_router`) fails in two directions:

1. **Too specific** — a macro `open https://…` breaks when the link, time, or event title changes, and cannot be shared without leaking someone else's meeting.
2. **Too generic** — “just tell the LLM to help” puts execution in the model, violating the C09 boundary.

A third failure mode is worse: treating `enigma://recipe/…` as a **script or prompt pack**. Arbitrary JS/Python, a hidden system prompt, or “ask the model to figure it out” turns a shared recipe into a **supply-chain and prompt-injection** channel. Untrusted content already arrives via mail ([ADR-021](./021-personal-data-security-boundary.md), [SEC-03](../../tickets/security/SEC-03-untrusted-content-adversarial-tests.md)); recipes must not open a second untrusted-execution path.

The missing object is a **shareable recipe**: a versioned, inspectable, declarative procedure over named Enigma capabilities. It is parameterised locally and executed deterministically by Enigma after approval.

This ADR is the North Star. It does **not** authorise a recipe engine, `enigma://` handler, or calendar-join implementation. Those wait on C09 conversational proof and [SEC-05](../../tickets/security/SEC-05-personal-data-pilot-gate.md) PASS. See [shareable-recipes.md](../architecture/shareable-recipes.md) and [REC00](../../tickets/recipes/REC00-shareable-recipes-north-star.md).

## Decision

### Core line

**Recipes contain procedure, never personal state.**

A recipe is a portable package of *how to pursue a goal using Enigma capabilities*. It is not a snapshot of a person's world, not a shortcut URL, not executable code, not a prompt bundle, and not a diagnostic label ([ADR-011](./011-observable-support-challenges-only.md)).

### Non-negotiable shape

| GOOD | BAD |
| --- | --- |
| Typed steps over named Enigma tools | Arbitrary JS / Python / shell |
| Declared capabilities with scope | Hidden or implied permissions |
| Explicit parameters (schema, not bound values) | Hardcoded URLs, event ids, tokens |
| Deterministic Enigma tools | Hidden system prompt / prompt pack |
| Inspectable manifest + plain-language install copy | “Ask the model to figure it out” |

If a recipe cannot be expressed as typed steps + declared capabilities + explicit parameters, it is not a recipe. `enigma://recipe` must not become a supply-chain or prompt-injection vector.

### Execution hierarchy

```text
LLM understands intent
    ↓
Recipe describes how
    ↓
Enigma supplies private truth
    ↓
Policy permits
    ↓
Assist approval
    ↓
Executor performs + verifies
```

| Layer | Responsibility |
| --- | --- |
| **LLM** | Match natural-language goal → recipe id (or no match). No world facts, no steps invented, no execution. |
| **Recipe** | Declarative how: intention, versioned manifest, typed steps, required capabilities, inputs, effects. |
| **Private world model** | *This* user's event, URL, joinability, attention set, mail — never in the package. |
| **Policy** | Capability grants, scope, A0–A5 rung, Demo/Private/Shadow roots. Default deny. |
| **Assist** | Structured preview; explicit approval. Recipes do not skip rungs. |
| **Executor** | Perform granted steps; **VERIFIED** only after outcome confirmation ([ADR-019](./019-delegated-authority-and-execution-ladder.md)). |

Same Assist lifecycle as today: **PROPOSED → APPROVED → EXECUTING → VERIFIED**.

### Inspectable manifest

Every shareable recipe carries a machine-readable manifest and a **normal-language** install summary. Minimum fields:

| Field | Role |
| --- | --- |
| `name` | Human id (e.g. `adhd-body-double`) |
| `version` | Semver; grants are per version |
| `inputs` | Parameter schema only (not bound values) |
| `capabilities` | Named capabilities **with scope** |
| `effects` | External / world-model effects |
| `network_access` | Must be `false` unless a future ticket explicitly opens a declared, scoped network capability |
| `arbitrary_code` | Must be `false` |
| `arbitrary_prompt` | Must be `false` |

Provenance (publisher, content hash, version) is part of the install record. Unsigned or unversioned packages are rejected.

On **[Add recipe]**, Enigma shows what it can and cannot do in ordinary language, then asks for grants. Example:

> This recipe can look up today's matching calendar event and open its join link in your browser. It cannot send email, read your mail, or run code. Adding it will ask you to allow calendar lookup and opening a browser to the event's own join URL.

### Version + provenance + permission re-evaluation

A grant is keyed by **(recipe id, version, capability set)**. Existing grants **do not silently carry over** when capabilities grow.

Example:

- Recipe **v1** declares `calendar.read` + `browser.open`. User grants v1.
- Recipe **v2** adds `email.send`.

v1's grant is **not** a grant of v2. Enigma must re-present the new capability set and obtain explicit approval for `email.send` (and any other newly declared capability or widened scope) before v2 may run. Narrowing capabilities may still require a version bump so the installed copy is auditable; widening always requires a new decision.

### Sharing: procedure only, local execution

Alice's recipe is procedure. Oscar installing it runs against **Oscar's** world, **Oscar's** permissions, **Oscar's** Assist approval. Tobi installing the same recipe runs against **Tobi's**. The package never contains Alice's event, Oscar's join URL, or anyone's grants.

A community name such as `enigma://recipe/adhd-body-double` names a **practice**, not the installing user. Installing it must not write a condition onto the person record ([ADR-011](./011-observable-support-challenges-only.md)).

### Capability-scoped, not data access

Recipes reuse [ADR-015](./015-capability-scoped-disclosure-not-data-access.md): the recipe (then Enigma on the user's behalf) receives **capability grants**, not store access.

On **[Add recipe]**:

1. Enigma shows capabilities, scope, inputs, effects, and the three boolean flags.
2. User grants or denies each capability (default deny).
3. User binds local parameters (e.g. how to match “my ADHD call” on *their* calendar).
4. Shared package remains procedure; bindings and grants stay local.

The recipe cannot open an arbitrary URL, read the whole calendar, send mail, or suppress all attention unless those capabilities were declared **and** granted for **this version**.

### Inter-Enigma

A later recipe may include a step such as `propose.shared_event`. That does **not** bypass the coordination protocol. Cross-boundary steps still emit typed signed envelopes, still require capability grants and bilateral consent, and still sit on the A0–A5 ladder ([ADR-013](./013-inter-enigma-coordination-trust-boundary.md)–[ADR-019](./019-delegated-authority-and-execution-ladder.md)). Incoming peer messages remain evidence, not truth.

### What a recipe may contain

- Intention / recipe id (e.g. `JOIN_SUPPORT_CALL`)
- Version, provenance, inspectable manifest
- Human-readable goal and non-goals (“can / cannot”)
- Required **capabilities with scope**, **inputs**, **effects**
- Ordered **typed** steps as named Enigma tool invocations (resolve → check → propose → act)
- Parameter schema with local defaults — not bound values
- Minimum authority rung per step
- `network_access: false`, `arbitrary_code: false`, `arbitrary_prompt: false`

### What a recipe must never contain

| Forbidden | Why |
| --- | --- |
| Arbitrary JS / Python / shell | Supply-chain; unauditable execution |
| Hidden system prompt or prompt bundle | Prompt injection via `enigma://recipe` |
| “Ask the model to figure it out” as a step | Authority leak ([ADR-020](./020-llm-conversational-boundary-not-truth.md)) |
| Join URLs, meeting IDs, calendar event ids | Personal state; not portable; leaks if shared |
| Hardcoded event titles as “the” event | Fails for everyone else's calendar |
| `PrivatePerson`, attendee emails, Notes, mail bodies | Privacy invariant |
| OAuth tokens, capability grants, local permissions | Grants are Enigma’s, per install, per version |
| Diagnostic labels as required user traits (`ADHD=true`) | [ADR-011](./011-observable-support-challenges-only.md) |
| “Just do it” / auto-execute flags that bypass Assist | [ADR-019](./019-delegated-authority-and-execution-ladder.md) / C07 |
| Silent inheritance of prior-version grants | Permission re-evaluation |

### LLM matches; execution is deterministic

The LLM may say “this utterance is `JOIN_SUPPORT_CALL`.” It may **not** invent steps, pick a Zoom link from weights, skip the joinable check, or execute. Unmatched goals do not become improvised recipes.

If the bound event cannot be resolved, or the URL is missing, or the slot is not joinable yet — Enigma reports that from the world model. The model does not guess.

### Parameterised locally

Shared procedure is generic (`event_match`, `open_before_minutes`). Bound values are per-user configuration. The same recipe adapts to *my* calendar, *my* link, *my* permissions.

### Illustrative (not an implementation spec)

**Goal:** “I need to join my ADHD call.”

**Not:** `open https://zoom.us/j/…`

**Procedure:** resolve today's matching event → read that event's join URL → check joinable given `open_before_minutes` → propose open URL → on approval, open → optionally propose suppressing unrelated attention.

Other North Star examples (catalogue only): Get me out the door; reply to an avoided loop; 20-minute admin reset; prepare for the next meeting.

## Sequencing (hard)

Do **not** implement a recipe runtime now.

| Prerequisite | Why |
| --- | --- |
| [C09](../../tickets/conversational-ui/C09-llm-conversational-boundary.md) **LLM proof** (not harness-only) | Goal → recipe id is LLM matching over a tool/registry boundary; regex phrase families stay frozen |
| [SEC-05](../../tickets/security/SEC-05-personal-data-pilot-gate.md) PASS | External effects (open URL, calendar resolve, attention suppress) on Private data require the personal-data gate |

C09 v1 (tool registry on Demo) is necessary but not sufficient. Recipes that touch a real calendar or browser are a post-pilot concern. Parked ticket: [REC00](../../tickets/recipes/REC00-shareable-recipes-north-star.md).

## Consequences

- Product does not grow a zoo of hardcoded EF buttons; patterns arrive as inspectable, versioned recipes.
- Sharing is procedure-shaped (`enigma://recipe/…`), inspectable before add — capabilities, can/cannot, then grant **this version**.
- Conversational UI gains a future tool family (`recipe.match` / `recipe.run`) that still cannot auto-execute ([ADR-020](./020-llm-conversational-boundary-not-truth.md)).
- Coordination recipes (cross-Enigma, e.g. `propose.shared_event`) still emit signed envelopes under ADR-013–019; this ADR does not replace the coordination protocol.
- Agents must not land a recipe engine, URL scheme, interpreter, or “join ADHD call” feature under conversational-ui, Demo, or security tickets.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Hardcoded product flows per pattern | Does not scale; encodes one person's calendar into the app |
| Bookmarklet / URL macro | Not intention-preserving; shares or freezes personal links |
| LLM plans and executes each time | Authority leak; non-deterministic side effects; unauditable |
| Prompt bundle / hidden system prompt as the recipe | Prompt injection; `enigma://recipe` becomes untrusted instruction |
| Arbitrary JS/Python in the package | Supply-chain; cannot inspect effects; bypasses tool registry |
| Share world-model snippets (“here is my Tuesday 8pm event”) | Personal state in the package; privacy failure |
| Global “allow recipes to act” toggle | Violates capability-specific grants ([ADR-015](./015-capability-scoped-disclosure-not-data-access.md), [ADR-019](./019-delegated-authority-and-execution-ladder.md)) |
| Silent grant carry-over across versions | New capabilities (e.g. `email.send`) must be re-approved |

## Related

- [north-star.md](../architecture/north-star.md) — recipes encode procedure; share how, never personal state
- [shareable-recipes.md](../architecture/shareable-recipes.md) · [REC00](../../tickets/recipes/REC00-shareable-recipes-north-star.md)
- [ADR-015](./015-capability-scoped-disclosure-not-data-access.md) · [ADR-019](./019-delegated-authority-and-execution-ladder.md) · [ADR-020](./020-llm-conversational-boundary-not-truth.md)
- [ADR-013](./013-inter-enigma-coordination-trust-boundary.md)–[ADR-016](./016-bilateral-consent-and-shared-commitments.md) — cross-boundary recipe steps
- [ADR-011](./011-observable-support-challenges-only.md) · [executive-function-support-benchmark.md](../architecture/executive-function-support-benchmark.md)
- [conversational-ui.md](../architecture/conversational-ui.md) · [C09](../../tickets/conversational-ui/C09-llm-conversational-boundary.md)
- [ADR-021](./021-personal-data-security-boundary.md) · [SEC-03](../../tickets/security/SEC-03-untrusted-content-adversarial-tests.md) · [SEC-05](../../tickets/security/SEC-05-personal-data-pilot-gate.md)
- [ADR-026](./026-ethics-creed-user-is-subject.md) · [ethics.md](../architecture/ethics.md) — recipes carry procedure, never a person's world
