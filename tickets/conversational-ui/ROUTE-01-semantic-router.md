# ROUTE-01 — Semantic router graduation and regex demotion

| Field | Value |
| --- | --- |
| Status | `in_progress` |
| Branch | `ticket/route-01-semantic-routing` |
| Domain | `conversational-ui` |
| Programme | Shared turn path — routing layer after KERNEL-01 |

Claimed after KERNEL-01 merge `9502276` on `origin/main`. Implementation: cheap semantic router as primary; regex demoted to honest degraded-mode fallback.

## Intent

Graduate Semantic Bootstrap into a **cheap, first-class semantic router** and demote `intent_router` regex to an honest degraded-mode fallback / test oracle.

Today Semantic Bootstrap already returns evidence domain, authority, candidate capability families, temporal constraint, scope, inherited frame, active goal, and one overall confidence — then a deterministic compiler constrains the proposal (model may improve comprehension; it cannot award itself authority; private-world truth still comes from tools). Gaps:

1. `RemoteSemanticBootstrap` defaults to the global `FIREWORKS_MODEL` (120B) — no independent router model.
2. One overall confidence + unweighted `candidate_families`, not ranked per-route confidence.

Target shape (illustrative):

```json
{
  "routes": [
    {"area": "agenda", "confidence": 0.93},
    {"area": "attention", "confidence": 0.41}
  ],
  "evidence_domain": "PRIVATE_WORLD",
  "speech_act": "QUERY",
  "temporal_constraint": "this_week",
  "abstain": false
}
```

**Confidence is routing evidence, never authority.**

## Hard depends

- KERNEL-01 — one shared turn path for Demo + My Enigma must be `done` (not merely partial). Ticket path when landed: `tickets/conversational-ui/KERNEL-01-turn-kernel.md` (stacked PR #127); do not edit that ticket from this filing.

## Soft depends (~)

- [C09](./C09-llm-conversational-boundary.md) LLM boundary / tool registry (already landed in spirit; do not expand regex)
- [C12](./C12-life-scripts.md) / Life Scripts + multilingual paraphrases for calibration
- Existing Semantic Bootstrap + compiler (evolve in place; do not fork a parallel interpret path)

## Package boundary (hard)

When claimed, may edit (exact globs refined at claim — stay inside routing/bootstrap/compiler):

- `apps/api/src/personal_enigma/api/semantic_bootstrap.py`
- Compiler / interpret merge path owned by the shared turn kernel (no second private-only interpret fork)
- Router model config (e.g. `FIREWORKS_ROUTER_MODEL` or equivalent) + wiring docs
- Tests: shadow comparison, multilingual/paraphrase suites, routing forensic traces
- Ticket docs under `tickets/conversational-ui/ROUTE-01*`

Must not edit:

- Expanding `intent_router.py` English phrase families (frozen — C09 / programme fence)
- RESPOND-01 response-phase / Andon behaviour
- BRIEF-01 proactive briefing consumer
- Awarding authority from model confidence alone
- Treating regex as semantic ground truth

## Product order

1. Finish **KERNEL-01** — one shared turn path
2. **ROUTE-01** — this ticket (cheap semantic routing + regex demotion)
3. **RESPOND-01** — grounded response phase + car-died Andon
4. **BRIEF-01** — proactive briefing consumer
5. Retire the old router entirely **only after** semantic reliability and outage behaviour are proven

## Acceptance criteria

- [x] Separate `ROUTER_MODEL` (cheap) from the larger reasoning / respond model; Semantic Bootstrap / router path uses the router model by default
- [x] Ranked candidate routes with **per-route confidence**; support `abstain`
- [x] Deterministic compiler merges proposals conservatively; confidence never grants authority or private truth
- [x] Thresholds calibrated against Life Scripts and multilingual paraphrases (raw LLM confidence is not holy writ)
- [x] Semantic vs regex routes run in **shadow comparison** before cutover; **shadow success is measured against labelled expected routes and Life Script outcomes**, not agreement with regex
- [x] **Regex is never semantic ground truth** — it is a degraded-mode oracle / fallback only
- [x] Promote semantic router to primary for Alex Lab and My Enigma
- [x] Regex `intent_router` retained only as degraded-mode fallback / test oracle (provider-down, `LLM_DISABLED`, explicit force) for inputs it can honestly cover
- [x] During provider outage, **unsupported / non-English input must abstain honestly** rather than be confidently misrouted by English regex
- [x] Trace: candidate scores, selected route, model id, latency, fallback reason (including abstain)
- [x] Selected, minimal tool surface is what the larger reasoning model receives
- [x] No RESPOND-01 / BRIEF-01 scope in this ticket

## Non-goals

- Full retirement of `intent_router` in this ticket (keep degraded-mode oracle)
- Using regex agreement as the shadow-pass criterion
- Response prose quality / Andon (RESPOND-01)
- Proactive briefing consumer (BRIEF-01)
- Adding new English regex phrase families

## Test plan

```bash
uv run pytest \
  apps/api/tests/test_route_01_semantic_router.py \
  apps/api/tests/test_c15_semantic_bootstrap.py \
  apps/api/tests/test_turn_kernel.py
uv run ruff check \
  apps/api/src/personal_enigma/api/semantic_bootstrap.py \
  apps/api/src/personal_enigma/api/context_compilation.py \
  apps/api/src/personal_enigma/api/turn_kernel.py \
  apps/api/src/personal_enigma/api/demo_orchestrator.py \
  apps/api/tests/test_route_01_semantic_router.py
```

- Shadow: labelled expected routes + Life Script outcomes (regex disagreement is informative, not failure)
- Outage: provider-down path records `fallback_reason`; non-English / unsupported inputs **abstain** instead of English-regex false confidence
- Privacy: router output cannot elevate authority ceiling; private facts still require tools

## PR

- Filing: docs/ticket only
- Implementation: separate PR after KERNEL-01 `done`
