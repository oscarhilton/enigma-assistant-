# ADR-026: Ethics creed — the user is the subject, never raw material

**Status:** Accepted  
**Date:** 2026-08-17

> **The user is the subject of Enigma, never its raw material.**
>
> Know only what is necessary. Infer only for a purpose. Remember less than you could. Make memory and action inspectable.

## Context

[ADR-021](./021-personal-data-security-boundary.md)–[023](./023-persistent-shadow-abstract-state-not-biography.md) specify **how** Enigma stores, forgets, and egresses. [ADR-015](./015-capability-scoped-disclosure-not-data-access.md)–[016](./016-bilateral-consent-and-shared-commitments.md) specify **how** Enigmas may ask each other. [ADR-024](./024-shareable-recipes-procedure-never-personal-state.md) and [ADR-025](./025-tone-memory-how-to-speak-not-who-you-are.md) name objects that must not become personal dossiers.

Those ADRs do not name the **subject/object** relationship. Without it, a system can satisfy encryption, TTLs, and reconstructability scores while still treating a human as something to complete, profile, or steer.

Alex is a **fictional synthetic** crash-test dummy. Investigating him is how we break Enigma before real people. That work is not a licence to write a biography of Alex or to ship detective-shaped memory for Oscar.

## Decision

1. **The ethics creed is a binding product constraint**, not optional philosophy. Full lines: [ethics.md](../architecture/ethics.md).
2. **The fifth line is the relationship:** the user is the subject of Enigma, never its raw material.
3. **Curiosity is not a retention justification.** The detective-show trap — keep or reconstruct because you *could* — is a FAIL, scored by [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md).
4. **Never secretly profile.** Inspect ("What do you remember?", "Why?", "Forget that") is mandatory surface, not a debug leftover.
5. **Alex remains a dummy.** Do not create `ALEX_BIOGRAPHY.md`. Scenario truth stays in fixtures and evaluator ground truth.
6. **This ADR authorises no new runtime.** It binds design, copy, retention, Cortex, recipes, tone, and the personal-data pilot. Real inbox still waits on C09 + SEC-05 PASS.

## Consequences

- Security PASS is necessary and not sufficient: a complete encrypted model of a human still fails the creed.
- Third parties who appear in mail/calendar are not silently dossiered.
- Sensitive inferences (late reply ≠ depressed / cheating / financially distressed) stay in the [sensitive class](../architecture/data-retention.md#sensitive-inferences-special-class).
- Cross-user access remains capability + consent; never covert query.
- Cortex shows **system events**, not thoughts, emotions, or consciousness.
- Behavioural influence aligns to **explicit** goals and wellbeing — not silent optimisation of productivity, engagement, purchases, or politics.
- [tickets/security/README.md](../../tickets/security/README.md): ethics creed before real inbox.

## Alternatives considered

| Alternative | Why rejected |
| --- | --- |
| Ethics as README colour only | Mechanics would outrun the subject/object rule |
| Fold into ADR-023 reconstructability | Shape of shadow ≠ whether the user is raw material |
| Fold into ADR-011 (no diagnostic labels) | Broader than benchmarks; covers third parties, influence, Cortex |
| ALEX_BIOGRAPHY.md as "author notes" | Normalises biography-shaped artefacts; dummy becomes a person file |
| "Complete the model, then minimise" | Curiosity-as-justification; fails "remember less than you could" |

## Related

- [north-star.md](../architecture/north-star.md) — user is the subject; curiosity ≠ retention
- [ethics.md](../architecture/ethics.md)
- [ADR-023](./023-persistent-shadow-abstract-state-not-biography.md) · [data-retention.md](../architecture/data-retention.md) · [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md)
- [ADR-024](./024-shareable-recipes-procedure-never-personal-state.md) · [REC00](../../tickets/recipes/REC00-shareable-recipes-north-star.md)
- [ADR-025](./025-tone-memory-how-to-speak-not-who-you-are.md) · [tone-memory.md](../architecture/tone-memory.md)
- [ADR-015](./015-capability-scoped-disclosure-not-data-access.md) · [ADR-016](./016-bilateral-consent-and-shared-commitments.md) · [ADR-011](./011-observable-support-challenges-only.md)
- [cortex-visualizer.md](../architecture/cortex-visualizer.md)
