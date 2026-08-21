# ADR-043: Cheap semantic router is primary; regex is a degraded-mode oracle

## Status

Accepted

## Context

KERNEL-01 landed one shared turn path for Alex Lab and My Enigma (`9502276`). Language interpretation still had two gaps:

1. `RemoteSemanticBootstrap` defaulted to `FIREWORKS_MODEL` (120B) — the same large respond / reason model.
2. `intent_router` English regex remained close to the live path, and could confidently misroute non-English or unsupported input during provider outage.

ROUTE-01 graduates Semantic Bootstrap into a **cheap, first-class semantic router**. Regex agreement is not semantic ground truth.

## Decision

1. **Separate models.** `FIREWORKS_ROUTER_MODEL` (default `llama-v3p2-3b-instruct`) is the router. `FIREWORKS_MODEL` remains the larger respond / reason model. The router path must not silently fall back to 120B.
2. **Ranked routes + abstain.** The small model returns `{area, confidence}` candidates and may abstain. Confidence is routing evidence for the compiler, never authority or private-world truth.
3. **One interpret merge.** Demo and My Enigma share `interpret_with_router` → conservative merge → compiler. No private-only interpret fork. Ranked routes may minimise the tool surface the large model receives.
4. **Regex is degraded-mode only.** `intent_router` stays frozen as fallback / test oracle when the provider is down, `LLM_DISABLED=1`, or `ENIGMA_FORCE_REGEX_ROUTER=1` — and only for English it can honestly cover.
5. **Honest outage.** Unsupported or non-English input must abstain rather than be misrouted by English regex. Shadow success is labelled expected routes and Life Script outcomes, not regex agreement.

```text
USER
  ↓
CHEAP ROUTER (FIREWORKS_ROUTER_MODEL)
  ranked routes · abstain · no private world
  ↓
DETERMINISTIC COMPILER
  merge conservatively · confidence ≠ authority
  ↓
MINIMAL TOOL SURFACE
  ↓
LARGER RESPOND / REASON MODEL (FIREWORKS_MODEL)
```

## Consequences

- Alex Lab and My Enigma use the semantic router as primary when a provider key is present.
- Fixture / labelled oracles are tests, not production routing and not new regex.
- RESPOND-01 (grounded prose / Andon) and BRIEF-01 (proactive briefing consumer) stay out of this ticket.
- Full retirement of `intent_router` waits until semantic reliability and outage behaviour are proven.

## Related

- [ADR-020](./020-llm-conversational-boundary-not-truth.md) — LLM interprets; Enigma holds truth
- [ADR-029](./029-context-compilation-request-shaped-memory.md) — request-shaped compiler
- [ROUTE-01](../../tickets/conversational-ui/ROUTE-01-semantic-router.md)
- [KERNEL-01](../../tickets/conversational-ui/KERNEL-01-turn-kernel.md)
