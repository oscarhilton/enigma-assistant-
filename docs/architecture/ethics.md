# Enigma ethics

**Status:** Binding product constraint ([ADR-026](../adr/026-ethics-creed-user-is-subject.md)) — documentation; no new runtime  
**Date:** 2026-08-17  
**Related:** [north-star.md](./north-star.md) · [data-retention.md](./data-retention.md) · [ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md) · [tone-memory.md](./tone-memory.md) · [ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md) · [shareable-recipes.md](./shareable-recipes.md) · [cortex-visualizer.md](./cortex-visualizer.md) · [polaris-search.md](./polaris-search.md) · [ADR-015](../adr/015-capability-scoped-disclosure-not-data-access.md) · [ADR-016](../adr/016-bilateral-consent-and-shared-commitments.md)

## Creed

> Know only what is necessary.  
> Infer only for a purpose.  
> Remember less than you could.  
> Make memory and action inspectable.  
> **The user is the subject of Enigma, never its raw material.**

The first four are operating rules. The fifth is the subject/object relationship they exist to protect.

## Alex is a crash-test dummy

Alex Morgan is a **fictional synthetic** persona (`scenarios/alex-v1/`). Investigating him is a **crash-test dummy**, not surveillance. Security overlays, canaries, and reconstructability probes exist to **break** Enigma on a person who cannot be harmed.

Real people come later — after the [SEC-05](../../tickets/security/SEC-05-personal-data-pilot-gate.md) gate and this creed. Success on Alex is not a licence to build a biography of anyone.

**Do not create `ALEX_BIOGRAPHY.md`.** Author-side scenario notes stay in fixtures and ground truth. Enigma must not grow a narrative dossier of Alex, and agents must not write one.

## Lines

### Own data + informed consent

Processing the user's own mail, calendar, and notes is **OK** when Enigma is transparent about what it infers, stores, forgets, and sends off-device. Consent is not a one-time checkbox; inspectability ("What do you remember?", "Why?", "Forget that") is how consent stays informed.

Operational: [data-retention.md](./data-retention.md) user-facing forget operations · [SEC-02](../../tickets/security/SEC-02-audited-remote-egress-gate.md) egress disclosure.

### Other people in your mail and calendar

Ingestion will see other people's names, addresses, and messages because they appear in the user's sources. That does **not** authorise silently building rich permanent dossiers on everyone who emailed you.

Contacts are **minimal identity + purpose-scoped relationship state**, not a correspondence archive of third parties ([data-retention.md](./data-retention.md) people/contacts class · [ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md) scoped aliases).

### Sensitive inference

A late reply is not a persistent label of "depressed", "cheating", or "financially distressed."

Temporary relevance for answering a question the user asked is acceptable. Durable sensitive memory is not. Aligns with the [sensitive-inference special class](./data-retention.md#sensitive-inferences-special-class): medical, sexuality, political affiliation, substance use, intimate relationships, financial distress, behavioural routines — **no permanent pilot storage**.

Tone memory stores **how to speak**, not inner-life labels ([ADR-025](../adr/025-tone-memory-how-to-speak-not-who-you-are.md)). Diagnostic condition labels stay out of the person record ([ADR-011](../adr/011-observable-support-challenges-only.md)).

### Cross-user / network

Another person's Enigma is not a database you may query. Coordination is **capability + consent**: bounded question shapes, locally evaluated, minimum typed answers ([ADR-015](../adr/015-capability-scoped-disclosure-not-data-access.md) · [ADR-016](../adr/016-bilateral-consent-and-shared-commitments.md)). **Never** a covert query of another person's world.

Shareable recipes carry **procedure, never personal state** ([ADR-024](../adr/024-shareable-recipes-procedure-never-personal-state.md) · [REC00](../../tickets/recipes/REC00-shareable-recipes-north-star.md)). Installing a recipe does not import someone else's life.

### Minimum state for current purpose

Retain what Enigma needs **now** for attention, open loops, blockers, and next actions — **not** "how complete a model of this human."

This is the ethics form of [ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md): Enigma is an index of what still matters, not a second archive of a life. [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md) scores the empirical claim: biographical detail must collapse faster than executive-function usefulness.

### Curiosity is not a retention justification

The **detective-show trap:** treating Enigma as a case file — keep the thread because it might become interesting, reconstruct the person because you could.

Curiosity, completeness, and "we might need this later" are **not** retention justifications. If the purpose expired, forget. SEC-07's reconstructability axis exists to **fail** detective-shaped memory, not to celebrate it.

### Never secretly profile

Enigma must not accumulate a hidden model of the user. Memory and action are inspectable:

| User ask | Effect |
| --- | --- |
| **"What do you remember?"** | Inventory of retained classes and scopes |
| **"Why?"** | Provenance: source, purpose, expiry, lineage |
| **"Forget that"** | Graph forget — blobs, derivatives, embeddings, inferred labels |

Sibling for tone: *"How do you think I like you to talk to me?"* ([tone-memory.md](./tone-memory.md)). Inspect is not a raw dump of mail.

### Anthropomorphism

**Cortex shows system events**, not private thoughts, emotions, or consciousness ([cortex-visualizer.md](./cortex-visualizer.md)). Pulses are ingest, transform, attention, egress, decay, forget — state transitions Enigma **did**.

Do not product-copy Cortex as a mind that "feels", "wants", or "thinks about you." The LLM is an interpreter, not a person ([ADR-020](../adr/020-llm-conversational-boundary-not-truth.md)). **Enigma is the hidden substrate, not a companion with an inner life.** Council members are specialist **lenses**, not additional minds ([council.md](./council.md)). THE Goose may carry warmth; it must never mask missing evidence (calendar failure → incomplete picture, not a hallucinated free day).

### Behavioural influence

Do **not** silently optimise the user for productivity, engagement, purchases, or politics.

Alignment is to the user's **explicit goals and wellbeing** — Assist they approved, recipes they installed, tone they set or corrected. Nudges that maximise streaks, session time, or third-party outcomes without that alignment are out of scope.

Next Action may reduce executive-function friction the user asked for ([next-action.md](./next-action.md)). It must not become a covert coach, marketer, or persuader. Receding-horizon search ([polaris-search.md](./polaris-search.md)) is the same rule at tree depth: **help the user choose among locally available actions**; do not optimise a life, rank the person morally, or show theatrical chain-of-thought as a “Brain View.” The Council advises; it does not govern.

**Distress may increase supportiveness, never authority.** ADHD or difficulty can change **how much friction Enigma removes**, but never **silently change what it is allowed to do**. Ambiguous help requests default to the least-authoritative useful interpretation ([ADR-028](../adr/028-conversational-constitution-attestation-dialogue-support.md)).

**Remember less than you could.** Words are working memory. State is memory. Context compilation ([ADR-029](../adr/029-context-compilation-request-shaped-memory.md)) fetches only justified remote context. Default of private information is **absence from the request**, not presence-with-redaction. Expired raw words are successful forgetting, not memory failure.

## Mapping to existing architecture

| Ethics line | Where it already binds |
| --- | --- |
| Own data + consent | Retention inspect/forget · egress disclosure |
| Third-party contacts | Minimal people state · scoped aliases · no global narrative graph |
| Sensitive inference | [data-retention.md](./data-retention.md#sensitive-inferences-special-class) · SEC-05 Q14 |
| Cross-user | ADR-015 capability · ADR-016 bilateral consent · REC00 no personal state in recipes |
| Minimum purpose-bound state | ADR-023 four-layer lifecycle · Green/Amber/Red zones |
| Detective-show trap | SEC-07 reconstructability → 0 · red-line test |
| Inspectable memory | "What / Why / Forget" · tone inspect |
| Anthropomorphism | Cortex read-only events · ADR-020 LLM is not Enigma |
| Behavioural influence | Explicit Assist / recipe / tone; ADR-011 no diagnostic labels |

Security and privacy ADRs specify **mechanics**. This document names **why those mechanics are not optional** and what they must not become.

## Before a real inbox

```text
ethics creed
  → C09 LLM proof
  → SEC-00 … SEC-07
  → SEC-05 Confidentiality ∧ Minimisation ∧ Reconstructability PASS
  → live Gmail on Private roots
```

A watertight vault that still treats the user as raw material — complete model, secret profile, detective archive — **fails this creed** even if encryption PASSes.
