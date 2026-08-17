# Shareable recipes programme (REC00+)

**Status:** North Star captured — **parked**. Do not claim until C09 LLM proof **and** SEC-05 PASS.  
**North star:** Recipes contain procedure, never personal state. A recipe is a declarative procedure — not executable code, not a prompt bundle.

> Prefix is **REC**, not `R*` (Reasoning Value Gate) and not `SE*` / `SEC*`.

## Architectural rules (from ADR-024)

1. **Procedure only** — no personal state in the package (no URLs, event ids, grants, Notes, mail, `PrivatePerson`).
2. **Declarative** — typed steps, declared capabilities with scope, explicit parameters, deterministic Enigma tools.
3. **Not code, not prompts** — `arbitrary_code: false`, `arbitrary_prompt: false`, `network_access: false`. Otherwise `enigma://recipe` is supply-chain / prompt-injection.
4. **Inspectable** — manifest + normal-language install copy before **[Add recipe]**.
5. **Versioned grants** — v1 `calendar.read` + `browser.open` does **not** silently authorise v2 `email.send`. Re-evaluate permissions per version.
6. **Local execution** — Alice's recipe runs in Oscar's world/permissions vs Tobi's.
7. **Hierarchy** — LLM understands intent → Recipe describes how → Enigma supplies private truth → Policy permits → Assist approval → Executor performs + verifies.
8. **Inter-Enigma steps** (e.g. `propose.shared_event`) still go through [ADR-013](../../docs/adr/013-inter-enigma-coordination-trust-boundary.md)–[019](../../docs/adr/019-delegated-authority-and-execution-ladder.md).

## Tickets

| Ticket | Title | Status |
| --- | --- | --- |
| [REC00](./REC00-shareable-recipes-north-star.md) | Shareable recipes North Star (docs) | future |

No implementation tickets until REC00 unparks.

## Docs

- [docs/adr/024-shareable-recipes-procedure-never-personal-state.md](../../docs/adr/024-shareable-recipes-procedure-never-personal-state.md)
- [docs/architecture/shareable-recipes.md](../../docs/architecture/shareable-recipes.md)
- Conversational boundary: [ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md) · [C09](../conversational-ui/C09-llm-conversational-boundary.md)
- Assist ladder: [ADR-019](../../docs/adr/019-delegated-authority-and-execution-ladder.md) · [C07](../conversational-ui/C07-assist-proposals.md)
- Coordination: [enigma-coordination-protocol.md](../../docs/architecture/enigma-coordination-protocol.md)
- Personal-data gate: [SEC-05](../security/SEC-05-personal-data-pilot-gate.md)
- Ethics: [ethics.md](../../docs/architecture/ethics.md) · [ADR-026](../../docs/adr/026-ethics-creed-user-is-subject.md) — procedure never personal state; no covert query

## Claim order

1. **C09** LLM proof (live model, not harness-only 19/19).
2. **SEC-05** PASS (all three dimensions).
3. Then unpark REC00 / follow-on implementation tickets.

Do **not** implement a recipe engine, `enigma://` handler, interpreter, or calendar-join under conversational-ui, Demo, or security tickets.

## Branch naming

`ticket/REC00-slug` …
