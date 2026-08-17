# REC00 — Shareable recipes North Star

**Status:** future  
**Branch:** `ticket/REC00-shareable-recipes-north-star`  
**Domain:** recipes (documentation now; runtime later)  
**Package boundary (docs capture):** `docs/adr/024-*.md`, `docs/architecture/shareable-recipes.md`, `tickets/recipes/**`, cross-links in `docs/architecture/overview.md`, `docs/architecture/conversational-ui.md`, `docs/architecture/enigma-coordination-protocol.md`, `docs/adr/013-*.md`, `docs/adr/015-*.md`, `docs/adr/019-*.md`, `docs/adr/020-*.md`, `tickets/README.md`, `tickets/conversational-ui/README.md`, `tickets/conversational-ui/C09-*.md`  
**Package boundary (implementation — do not start):** none claimed; do not add a recipes package, URL scheme, or engine under this ticket until unparked.

**Hard depends:** [C09](../conversational-ui/C09-llm-conversational-boundary.md) **LLM proof** (not harness-only); [SEC-05](../security/SEC-05-personal-data-pilot-gate.md) PASS  
**Soft (~):** [C07](../conversational-ui/C07-assist-proposals.md) Assist ladder already landed; [CO00](../coordination/CO00-adr-programme.md) if a recipe step is `propose.shared_event`

**Unlocks / enhances:** Future recipe engine, `enigma://recipe/…` install UX, first declarative EF recipes (join support call, out-the-door, admin reset) — **after** unpark only.

## Parked

```text
C09 LLM proof  →  SEC-05 PASS  →  unpark REC00 implementation
```

Do **not** implement now. Documentation capture below is the whole current scope.

## Goal

Name **shareable recipes** as North Star architecture: executive-function patterns as portable **declarative procedures**, never personal state, never executable code, never a prompt bundle.

Core line: **Recipes contain procedure, never personal state.**

## Documentation capture (this slice)

- [x] [ADR-024](../../docs/adr/024-shareable-recipes-procedure-never-personal-state.md)
- [x] [shareable-recipes.md](../../docs/architecture/shareable-recipes.md)
- [x] Programme README + this ticket
- [x] Cross-links (overview, conversational-ui, ADR-013/015/019/020, C09, tickets index)

## Non-goals

- Recipe engine, interpreter, package manager, or `enigma://` handler
- Join-call / out-the-door / admin-reset product features
- Arbitrary JS/Python or prompt-bundle formats
- Expanding `intent_router` phrase families
- Marketplace, signing CA, or trust scoring
- Diagnostic ADHD labels in the person record ([ADR-011](../../docs/adr/011-observable-support-challenges-only.md))

## Acceptance criteria (implementation — after unpark)

Do not work these until hard depends are green.

- [ ] Recipe is a versioned inspectable manifest: `name`, `version`, `inputs`, `capabilities` with scope, `effects`, `network_access: false`, `arbitrary_code: false`, `arbitrary_prompt: false`
- [ ] Install copy in normal language; **[Add recipe]** shows can / cannot, then per-capability grant (default deny)
- [ ] Typed steps invoke named Enigma tools only — tests reject arbitrary code and arbitrary prompts
- [ ] v1 grant (`calendar.read` + `browser.open`) does **not** authorise v2 `email.send`; user must approve the new capability
- [ ] Shared package contains no personal state; same recipe on Oscar vs Tobi uses each person's world, grants, and executor
- [ ] LLM may match goal → recipe id; may not invent steps or execute ([ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md))
- [ ] Assist lifecycle **PROPOSED → APPROVED → EXECUTING → VERIFIED** ([ADR-019](../../docs/adr/019-delegated-authority-and-execution-ladder.md) / C07)
- [ ] Optional later step `propose.shared_event` still governed by [ADR-013](../../docs/adr/013-inter-enigma-coordination-trust-boundary.md)–[019](../../docs/adr/019-delegated-authority-and-execution-ladder.md)

## Test plan (after unpark)

- Manifest parser rejects `arbitrary_code: true`, `arbitrary_prompt: true`, missing version, and bound personal fields (URLs, event ids)
- Permission test: install v1, publish v2 with `email.send`, assert v2 cannot run on v1 grant
- Isolation test: Alice-authored fixture recipe + two Demo identities → distinct resolved events / no cross-leak
- C09: unmatched NL does not improvise a recipe; match calls `recipe.match` then Assist, never auto-execute

## Privacy constraints

No `PrivatePerson`, Notes, mail bodies, OAuth tokens, or grants in the shared package. Demo recipes use Demo roots only ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md)). Private external effects wait on SEC-05. Cross-boundary steps do not export world models ([ADR-013](../../docs/adr/013-inter-enigma-coordination-trust-boundary.md)). Recipes must not become a covert channel into another person's world — capability + consent only ([ethics.md](../../docs/architecture/ethics.md) · [ADR-026](../../docs/adr/026-ethics-creed-user-is-subject.md)).

## Notes

Prefix **REC00** avoids collision with Reasoning `R01`–`R07` and Shadow `SE*`. Agents must not land a recipe runtime “while here” on C09 or SEC tickets.
