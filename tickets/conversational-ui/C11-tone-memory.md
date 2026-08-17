# C11 — Tone memory (how to speak, not who you are)

**Status:** future  
**Branch:** `ticket/C11-tone-memory`  
**Domain:** conversational-ui (documentation now; runtime later)  
**Package boundary (docs capture):** `docs/adr/025-*.md`, `docs/architecture/tone-memory.md`, this ticket, cross-links in `docs/architecture/overview.md`, `docs/architecture/conversational-ui.md`, `docs/architecture/data-retention.md`, `docs/architecture/personal-data-security.md`, `docs/adr/020-*.md`, `docs/adr/022-*.md`, `docs/adr/023-*.md`, `tickets/README.md`, `tickets/conversational-ui/**`, `tickets/next-action/N03-*.md`  
**Package boundary (implementation — do not start):** none claimed; do not add a tone store, learner, or C09 payload field under this ticket until unparked.

**Hard depends:** [C09](./C09-llm-conversational-boundary.md) **LLM proof** (not harness-only)  
**Soft (~):** [SEC-01](../security/SEC-01-secrets-encrypted-storage.md) / [SEC-06](../security/SEC-06-retention-memory-decay-forget.md) for Private vault persistence; [C05d](./C05d-conversation-continuity.md) already landed (session referents ≠ tone)

**Unlocks / enhances:** Small REMOTE_SAFE tone profile on the C09 orchestrator instead of last-N chat; inspect/correct UX — **after** unpark only.

## Parked

```text
C09 LLM proof  →  unpark C11 implementation
```

Do **not** implement now. Documentation capture below is the whole current scope.

## Goal

Name **tone memory** as North Star architecture: Enigma may remember *how to communicate* without remembering the conversations that taught it how.

Core line: **Store style preferences, not a personality dossier / conversation logs.**

**Tone may transform expression; it may not transform state, urgency, recommendation strength, or authority.** It rides on the C09 respond phase — not a second personality LLM.

## Documentation capture (this slice)

- [x] [ADR-025](../../docs/adr/025-tone-memory-how-to-speak-not-who-you-are.md)
- [x] [tone-memory.md](../../docs/architecture/tone-memory.md)
- [x] This ticket + conversational-ui README
- [x] Cross-links (overview, conversational-ui, ADR-020/022/023, data-retention sensitive inferences, personal-data-security, C09, N03)

## Non-goals

- Tone store, learner, or C09 payload change **now**
- Sending last-N messages as style memory
- Continuous scores (`sarcasm_score`, profanity %)
- Psychological / political / medical profiling from discourse
- Promoting TURN-LOCAL affect ("frustrated now") into "user is irritable"
- Absorbing communication style into [N03](../next-action/N03-preference-learning.md) Next Action fitness
- Expanding `intent_router` phrase families
- Diagnostic labels on the person record ([ADR-011](../../docs/adr/011-observable-support-challenges-only.md))

## Acceptance criteria (implementation — after unpark)

Do not work these until C09 LLM proof is green.

- [ ] Three layers: USER-SET (durable, `EXPLICIT_USER`, confidence `1.0`), LEARNED (durable, `INFERRED`, weaker confidence, unreinforced decays), TURN-LOCAL (evaporates; never a person trait)
- [ ] Closed enum dimensions only: `directness`, `warmth`, `verbosity`, `humour`, `formality`, `encouragement`, `initiative`, `technical_depth`, `challenge_assumptions`, `avoid_productivity_cheerleading` — no continuous psychometrics
- [ ] Promotion ladder: observation → temporary signal → repeated → candidate → stable → decay; one turn never graduates
- [ ] Explicit correction wins immediately (e.g. `verbosity=LOW`, `source=EXPLICIT_USER`, `confidence=1.0`)
- [ ] C09 remote payload includes a **small** tone profile with `current_subject` + tool results — **not** last 200 messages
- [ ] Privacy class `PRIVATE_DERIVED_PREFERENCE` (subclass of `PRIVATE_DERIVED`); egress as coarse `REMOTE_SAFE` enums only
- [ ] Inspectable: "How do you think I like you to talk to me?" then user can correct
- [ ] Tests reject stored personality/political/medical inferences and reject durable "irritable" from a single turn

## Test plan (after unpark)

- Explicit "be concise" → `verbosity=LOW` / `EXPLICIT_USER` / `1.0`; subsequent compose uses the profile without a transcript
- Repeated LIGHT humour signals → candidate then stable `INFERRED` at confidence `< 1.0`; unreinforced decay
- One frustrated turn → TURN-LOCAL only; no durable irritability trait
- Orchestrator fixture: payload contains tone enums + subject + tools; assert absence of chat-log history and of psych-dossier fields
- Inspect/correct round-trip; forget of teaching conversation does not require dropping an explicit enum

## Privacy constraints

Tone memory is personal data. Less sensitive than raw conversation; still vault-only. Do not send transcripts, Notes, `PrivatePerson`, or psych labels to a hosted model. Demo and Private roots stay isolated ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md)). Align with the [sensitive-inference ban](../../docs/architecture/data-retention.md#sensitive-inferences-special-class).

## Notes

C11 is conversational-ui, not a new programme prefix. Agents must not land a tone runtime "while here" on C09, N03, SEC, or D08f tickets. The six-month ordinary-events corpus ([D08f](../demo-scenario/D08f-alex-six-month.md)) is the fixture for Jan signal → Feb repeat → Mar stable → Apr used → May/Jun decay — it does **not** unpark this ticket. N03 remains task-category fitness from Next Action rejects — different object.
