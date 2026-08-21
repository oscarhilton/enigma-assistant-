# Shareable recipes

**Status:** North Star — documentation only. No runtime.  
**Date:** 2026-08-17  
**Philosophy:** [north-star.md](./north-star.md) (squeeze 4 — recipes encode procedure)  
**ADR:** [024 — Shareable recipes — procedure, never personal state](../adr/024-shareable-recipes-procedure-never-personal-state.md)  
**Ticket:** [REC00](../../tickets/recipes/REC00-shareable-recipes-north-star.md) (parked)  
**Depends (hard, before any implementation):** [C09 LLM proof](../../tickets/conversational-ui/C09-llm-conversational-boundary.md) + [SEC-05 PASS](../../tickets/security/SEC-05-personal-data-pilot-gate.md)

> **Recipes contain procedure, never personal state.**
>
> A recipe is a **declarative procedure**: typed steps, declared capabilities, explicit parameters, deterministic Enigma tools. It is **not** executable code and **not** a prompt bundle.

## Why recipes exist

Executive-function patterns (“join the support call”, “get me out the door”, “20-minute admin reset”) should not be hardcoded into the product, and should not be re-invented by the LLM on every utterance.

A **shareable recipe** packages the *how* so Alice can publish a practice and Oscar or Tobi can install it. Each install binds to **that person's** world, permissions, and Assist approval. The package never carries personal state.

## Execution hierarchy

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

| Step | Who | Must not |
| --- | --- | --- |
| Understand intent | LLM ([ADR-020](../adr/020-llm-conversational-boundary-not-truth.md)) | Invent world facts, invent steps, execute |
| Describe how | Recipe manifest + typed step graph | Contain JS/Python, hidden prompts, personal data |
| Supply private truth | Enigma world model | Leak into the shared package |
| Permit | Capability policy + A0–A5 ([ADR-015](../adr/015-capability-scoped-disclosure-not-data-access.md), [ADR-019](../adr/019-delegated-authority-and-execution-ladder.md)) | Silent grant carry-over; global “trust recipes” toggle |
| Approve | Assist (C07) | Auto-execute |
| Perform + verify | Executor | Skip **VERIFIED**; treat proposal as done |

Lifecycle is unchanged: **PROPOSED → APPROVED → EXECUTING → VERIFIED**.

## Non-negotiable: declarative, not code, not prompts

`enigma://recipe/…` is a **capability-scoped procedure document**. If it can run arbitrary code or inject instructions into the model, it is a supply-chain and prompt-injection channel — the same class of hostility as untrusted email ([ADR-021](../adr/021-personal-data-security-boundary.md), [SEC-03](../../tickets/security/SEC-03-untrusted-content-adversarial-tests.md)).

| GOOD | BAD |
| --- | --- |
| Typed steps (`calendar.resolve_event`, `browser.open_url`) | Arbitrary JS / Python / shell |
| Declared capabilities with scope | Hidden permissions; “needs access to your account” |
| Explicit parameter schema | Hardcoded Zoom URL / event id |
| Deterministic Enigma tools | Hidden system prompt / prompt pack |
| Inspectable manifest + plain-language install copy | “Ask the model to figure it out” |

Required manifest flags:

- `network_access: false` — unless a future ticket names a **declared, scoped** network capability (not a general fetch).
- `arbitrary_code: false`
- `arbitrary_prompt: false`

A recipe that cannot set those three to `false` is not installable.

## Inspectable manifest

Illustrative shape (not a frozen schema — no implementation):

```yaml
name: adhd-body-double
version: "1.0.0"
intention: JOIN_SUPPORT_CALL
inputs:
  event_match: { type: string, description: "How to find today's call on MY calendar" }
  open_before_minutes: { type: integer, default: 5 }
capabilities:
  - { id: calendar.read, scope: "events matching event_match, today only" }
  - { id: browser.open, scope: "join URL from the resolved event only" }
effects:
  - open_browser_to_event_join_url
network_access: false
arbitrary_code: false
arbitrary_prompt: false
steps:
  - calendar.resolve_event
  - calendar.read_join_url
  - calendar.check_joinable
  - assist.propose_open_url
  - browser.open_url          # after approval
  - attention.propose_suppress_unrelated  # optional, after approval
min_rung:
  calendar.read: A0
  browser.open: A3
```

On **[Add recipe]** the user sees **normal language**, not YAML:

> **ADHD body-double (v1.0.0)**  
> This recipe can look up today's matching calendar event and open its join link in your browser.  
> It cannot send email, read your mail, run code, or talk to the internet except by opening that join link.  
> Adding it will ask you to allow: look up matching calendar events today; open a browser to the event's own join URL.

Then: capabilities used, what it can / cannot do, **[Add recipe]** → per-capability grant (default deny) → local parameter binding.

## Version, provenance, permission re-evaluation

Identity of an installed recipe is **(id, version, content hash, publisher)**.

A grant is keyed by **(recipe id, version, capability set)**. **Existing grants do not silently carry over** when a new version adds or widens capabilities.

```text
v1  calendar.read + browser.open     →  user granted v1
v2  calendar.read + browser.open + email.send
        ↓
v1 grant is not a v2 grant
        ↓
Enigma re-presents v2 capabilities
        ↓
user must approve email.send (and the new set) before v2 may run
```

Scope widening (e.g. `calendar.read` from “today / match” to “all calendars”) is the same class of change as adding a capability: new version, new decision.

Unsigned, unversioned, or hash-mismatched packages are rejected.

## Sharing: Alice’s procedure, Oscar’s world, Tobi’s world

Recipes **never** include personal state. Sharing copies procedure only.

```text
Alice authors JOIN_SUPPORT_CALL v1
        ↓
enigma://recipe/adhd-body-double@1.0.0
        ↓
    ┌───────┴───────┐
    ▼               ▼
 Oscar installs   Tobi installs
 Oscar's calendar Oscar-grants   Tobi's calendar Tobi-grants
 Oscar Assist     Oscar executor Tobi Assist     Tobi executor
```

Oscar's join URL never appears in what Tobi receives. Alice's Tuesday 8pm event never appears in the package. Local bindings (`event_match`, `open_before_minutes`) stay on the installing machine.

A community slug may name a **practice** (`adhd-body-double`). Installing it must not write `ADHD=true` (or any diagnostic) onto the person record ([ADR-011](../adr/011-observable-support-challenges-only.md)).

## Inter-Enigma

A later recipe may include `propose.shared_event` (or another coordination verb). That step is still governed by the capability/consent protocol:

- Typed signed envelopes only ([ADR-014](../adr/014-minimal-semantic-envelope-protocol.md))
- Capability grants, not data access ([ADR-015](../adr/015-capability-scoped-disclosure-not-data-access.md))
- Bilateral consent for shared facts ([ADR-016](../adr/016-bilateral-consent-and-shared-commitments.md))
- Assist rungs A3/A4 ([ADR-019](../adr/019-delegated-authority-and-execution-ladder.md))
- Incoming messages are evidence, not truth ([ADR-013](../adr/013-inter-enigma-coordination-trust-boundary.md))

The recipe does not become a backdoor past coordination. Private world models still do not cross the trust boundary.

## Canonical example: join support call

**Trigger (NL):** “I need to join my ADHD call.”

**Not:** `open https://zoom.us/j/…`

**How (recipe):** resolve today's matching event → read that event's join URL → check joinable given `open_before_minutes` → Assist propose open → on approval, open → optionally Assist propose suppressing unrelated attention.

**Truth (Enigma):** *this* user's calendar, *this* event's URL, *this* clock.

**Policy + Assist + executor:** grants for `calendar.read` + `browser.open` at the declared rungs; verified open.

The LLM's job is to recognise the goal as `JOIN_SUPPORT_CALL` (or no match). Unmatched goals do not become improvised recipes.

## Catalogue (illustrative only)

Not a product backlog. Not an implementation spec.

| Practice | Intention sketch |
| --- | --- |
| Join ADHD / body-double call | Resolve event → join URL → joinable → open |
| Get me out the door | Next leave constraint → checklist of local next actions → suppress noise |
| Reply to an avoided loop | Resolve waiting thread → draft locally → Assist send **only if** a send capability exists and is granted |
| 20-minute admin reset | Time-fit + bounded admin next-action set |
| Prepare for next meeting | Next event → materials / open loops tied to that event |

“Reply …” is listed to show that **send** is a separate capability. A v1 without `email.send` cannot grow it silently in v2.

## Sequencing

```text
C09 LLM proof  (model selects tools; harness-only is not enough)
    ↓
SEC programme → SEC-05 PASS  (Private external effects)
    ↓
REC00 unpark — recipe engine / enigma:// / first recipes
```

Until then: **capture ADR + this doc + REC00, then stop.** Do not implement a recipe engine, URL scheme, interpreter, calendar-join feature, or prompt-pack loader.

C09's Demo tool registry is the future `recipe.match` / `recipe.run` boundary — still no auto-execute.

## Non-goals (now)

- Recipe runtime, interpreter, or package manager
- `enigma://` handler
- Join-call product feature
- Arbitrary code or prompt-bundle formats
- Hardcoded EF buttons in conversational UI
- Expanding `intent_router` phrase families to match recipe goals
- Cross-Enigma recipe marketplace, trust scoring, or payment
- Diagnostic “ADHD mode”

## Related

- [ADR-024](../adr/024-shareable-recipes-procedure-never-personal-state.md) · [REC00](../../tickets/recipes/REC00-shareable-recipes-north-star.md)
- [conversational-ui.md](./conversational-ui.md) · [ADR-020](../adr/020-llm-conversational-boundary-not-truth.md) · [C09](../../tickets/conversational-ui/C09-llm-conversational-boundary.md)
- [ADR-019](../adr/019-delegated-authority-and-execution-ladder.md) · [C07](../../tickets/conversational-ui/C07-assist-proposals.md)
- [enigma-coordination-protocol.md](./enigma-coordination-protocol.md) · [ADR-013](../adr/013-inter-enigma-coordination-trust-boundary.md)–[ADR-019](../adr/019-delegated-authority-and-execution-ladder.md)
- [personal-data-security.md](./personal-data-security.md) · [SEC-05](../../tickets/security/SEC-05-personal-data-pilot-gate.md)
- [ethics.md](./ethics.md) · [ADR-026](../adr/026-ethics-creed-user-is-subject.md) — procedure never personal state; no covert query of another person's world
