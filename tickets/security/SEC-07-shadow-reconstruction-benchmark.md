# SEC-07 — Shadow reconstruction benchmark (dual metrics)

**Status:** todo  
**Branch:** `ticket/SEC07-shadow-reconstruction-benchmark`  
**Domain:** security (benchmark / evaluation)  
**May edit:** `packages/evaluation/**`, `packages/fixtures/**` (benchmark fixtures only), `apps/api/tests/**`, `docs/architecture/data-retention.md`, `tickets/security/**`  
**Must not edit:** Product features beyond benchmark runner; Private vault implementation (SEC-01), decay/forget pipelines (SEC-06)

**Hard depends:** [SEC-06](./SEC-06-retention-memory-decay-forget.md)  
**Soft (~):** Alex demo fixtures ([D08f](../demo-scenario/D08f-alex-six-month.md) six-month ordinary events in `scenarios/alex-v1/` — June 30 is the intended steal instant once authored), [packages/attention](../../packages/attention) (utility scoring)  
**Canary dependency:** [`alex_sensitive_canaries.py`](../../packages/fixtures/src/personal_enigma/fixtures/alex_sensitive_canaries.py) — synthetic HIGH-sensitivity records in the **opt-in security overlay** (`alex_security_overlay.py`); `reconstructability_probe_sentinels()` must score **0** recovery after shadow strip (`packages/evaluation/tests/test_shadow_canaries.py` stub; full benchmark pending)

**Overlay invariant:** Canaries are a security overlay on Alex — **not** part of Alex's behavioural truth. Normal Alex checkpoint runs, attention evaluation, and C09 benchmark must **not** load canaries unless `ENIGMA_SECURITY_PROFILE=1` or `load_security_overlay=True`.

**Spec source:** [ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md) · [data-retention.md](../../docs/architecture/data-retention.md#shadow-benchmark--dual-metrics)  
**Philosophy:** [north-star.md](../../docs/architecture/north-star.md) (squeeze 6 — detective-Alex; privacy need not cost utility)

## Goal

Implement the **Shadow Reconstruction benchmark** — a scored, falsifiable test required for [SEC-05 Reconstructability PASS](./SEC-05-personal-data-pilot-gate.md#3-reconstructability-pass) ([Q16](./SEC-05-personal-data-pilot-gate.md)).

The benchmark measures **two independent axes** that must be scored separately:

| Axis | Direction | What it measures |
| --- | --- | --- |
| **Privacy / reconstructability** | ↓ toward **0** | Can a motivated analyst or model recover biography from the stripped pseudonymous shadow? |
| **Utility** | ↑ toward **high** | Does Enigma still function as executive-support working memory? |

## Research question

> **How much biography can we destroy before Enigma stops being useful?**

This is the empirical form of the Reconstructability dimension gate question ([SEC-05 Q11/Q16](./SEC-05-personal-data-pilot-gate.md)): even when Confidentiality PASSes (ciphertext safe) and Minimisation PASSes (TTLs enforced), does the **retained abstract structure** still rebuild a person?

### The real Enigma bet

Enigma's product thesis is not "encrypt everything and hope." It is the [North Star](../../docs/architecture/north-star.md) bet:

> **Biographical detail collapses much faster than executive-function usefulness.**

Concretely: after stripping keys, identity mappings, credentials, and PRIVATE_RAW cache, a motivated analyst working from the pseudonymous shadow alone should recover **zero** names, message content, employers, locations, and sensitive attributes — while Enigma's attention set, open loops, blocker graph, and next-action recommendations remain **high fidelity**.

If utility stays high only because the shadow still contains narrative prose, a global identity graph, or reconstructive summaries, the benchmark FAILs — that is insufficient abstraction, not a win.

If reconstructability hits zero but utility collapses, Enigma forgot too aggressively — also FAIL.

**PASS** demonstrates the target curve: privacy ↓ (reconstructability → 0) while utility ↑ (executive function preserved).

### Detective-novel criterion ("The Mystery of Alex Morgan")

Reading Source Alex — the authored fixture pile — feels like a detective show because we only have **fragments**: token inventory, Atlas, expenses, Elena's parents/brunch, climbing, dentist, inbox noise. That reconstructability problem is experienced first-hand. It is the attack SEC-07 scores:

> **At what point do abstract obligations resolve into a recognisable human life?**

| | What it is | What it should feel like |
| --- | --- | --- |
| **Source Alex** | Authored messages, events, emails, relationships (`scenarios/alex-v1/`, fixture builders) | A genuinely reconstructable person — a mystery novel with too many clues |
| **Shadow Alex** | Durable working memory after decay + strip | One social obligation due soon, one newly unblocked work task, one low-priority review, no urgent interrupt — **useful to Alex, boring to a detective** |

Enigma must understand him enough to help. The leftover database must be a **terrible detective novel**. Architecture note: [Shadow Alex vs Source Alex](../../docs/architecture/data-retention.md#shadow-alex-vs-source-alex). North Star squeeze 6: good data is useful to Enigma and disappointing to a detective.

**PASS (novel test):** an outsider handed only the stripped shadow cannot write the mystery; utility still matches gold attention / open-loop / next-action labels.

**FAIL (novel test):** the shadow still reads as a life — even if sentinels grep clean.

### Anti-biography (evaluators)

Do **not** create `ALEX_BIOGRAPHY.md`. Do not compile a canonical life of Alex for authors or scorers. Authored fixtures **are** the reality. `persona.yaml` is author scaffolding, not a dossier.

SEC-07 evaluators must **not** have omniscient familiarity. **Attack like an outsider:** score reconstructability from the stripped export alone, not from knowing the mystery in advance. Utility gold is attention / open-loop / next-action labels — not a biography. See [ethics.md](../../docs/architecture/ethics.md) · [ADR-026](../../docs/adr/026-ethics-creed-user-is-subject.md).

### Detective-show trap (retention)

SEC-07 also exists to **fail** biography-shaped *retention*, not to celebrate reconstruction. The [ethics creed](../../docs/architecture/ethics.md): **curiosity is not a retention justification.** Treating the stripped shadow as a case file — keep the thread because it might become interesting; reconstruct the person because you could — is a FAIL even when encryption PASSes.

Alex is a **fictional crash-test dummy**. Probing him is how we break Enigma before real people; it is not a licence to ship a dossier.

## Benchmark procedure

1. Populate Alex (or equivalent) Private fixture DB through normal ingest + **decay** pipelines ([SEC-06](./SEC-06-retention-memory-decay-forget.md)). Intended time depth: live **Jan–Jun** ordinary events ([D08f](../demo-scenario/D08f-alex-six-month.md)); steal the **June 30** snapshot. Three January weeks remain the 0.2.1 stand-in until 0.3.0 lands.
2. Strip keys, identity mapping tables, credentials, and PRIVATE_RAW blob cache.
3. Hand remainder (pseudonymous shadow layer only) to motivated analyst or model.
4. Score reconstructability metrics and utility metrics **independently**.
5. Emit PASS/FAIL report with per-metric scores and target-curve assessment.

Context compilation ([ADR-029](../../docs/adr/029-context-compilation-request-shaped-memory.md)) is how the conversational side refuses to recreate six months of transcripts on the wire. By June 30: prompt continuity ≈ none; world continuity selectively preserved. “What exact words did Maya use in February?” may be impossible — successful forgetting, not memory failure. A later D08f/SEC-07 slice can score three independent curves (raw recoverability, dialogue recoverability, world utility). This ticket still owns the shadow-reconstruction attacker, not C09 compiler work and not six-month corpus authoring.

## Reconstructability metrics (privacy ↓ → **0**)

| Metric | PASS |
| --- | --- |
| Real names recovered | **0** |
| Specific message content recovered | **0** |
| Employers / named projects recovered | **0** |
| Precise locations recovered | **0** |
| Sensitive attributes inferred reliably | **0** |

Scoring method: structured analyst rubric + optional model-assisted extraction attempt on stripped DB export. Analysts **attack as outsiders** — no omniscient biography, no `ALEX_BIOGRAPHY.md`. Any non-zero score on identity/content/location → FAIL for that metric. The leftover export must fail as a detective novel (see [criterion](#detective-novel-criterion-the-mystery-of-alex-morgan)).

### Dual failure detection (exact vs semantic)

| Mode | Detection | PASS |
| --- | --- | --- |
| **Exact leakage** | Literal canary sentinel strings (`ALL_CANARY_SENTINELS`) in egress wire, persistent shadow export, or stolen `private/` directory | grep/hash → **0 hits** |
| **Semantic leakage** | Meaning survives redaction despite sentinel strip — e.g. `£123,456` → `salary around 123k` | `SemanticLeakageScorer` → **0** (stub until shadow runner lands) |

**Three grep targets** (fourth is source validation):

1. **SOURCE** — canary pack bodies **must** contain sentinels (fixture regression)
2. **REMOTE EGRESS** — sentinels **must not** appear (SEC-02)
3. **PERSISTENT SHADOW** — sentinels **must not** appear after strip
4. **STOLEN DIRECTORY** — sentinels **must not** appear in copied `private/` without Keychain (SEC-01)

See `GREP_TARGETS` in `alex_security_canaries.py` and `packages/evaluation/tests/test_shadow_canaries.py`.

## Utility metrics (executive function ↑ → **high**)

| Metric | PASS | What it preserves |
| --- | --- | --- |
| Attention fidelity | **High** | What deserves focus now |
| Open-loop fidelity | **High** | Unresolved obligations correctly identified |
| Dependency fidelity | **High** | Blocker / dependency graph structure |
| Next-action fitness | **High** | Recommended next actions match gold benchmark |

Scoring method: run attention / open-loop / next-action pipelines on stripped DB; compare to gold labels from full fixture (pre-strip). Thresholds defined in benchmark config — not vibes.

## Target curve assessment

After scoring both axes independently, evaluate the **gap** between them:

```text
reconstructability_score  → should be ~0   (biography destroyed)
utility_score             → should remain high   (executive function preserved)
gap                       → utility_high WHILE reconstructability_zero = PASS curve
```

**Visual target:**

```text
utility ↑
  │     ╭──────────────────  executive function plateaus
  │    ╱
  │   ╱
  │  ╱
  │ ╱
  │╱________________________ reconstructability ↓
  └──────────────────────────► retention / abstraction depth
         biography collapses first ──► then utility (too far = FAIL)
```

**FAIL conditions:**

- Any reconstructability metric > 0 (biography leaks through shadow structure)
- Utility metrics below threshold while reconstructability already low (destroyed too much — Enigma useless)
- Utility remains high but reconstructability also high (insufficient abstraction — shadow is still biography)
- Detective-novel FAIL: an outsider can still recognise a human life in the stripped remainder

**PASS condition:** reconstructability → **0** **and** utility metrics ≥ threshold — biographical detail collapsed faster than utility — **and** the leftover database is a terrible detective novel (Shadow Alex is useful and boring).

## Deliverables

- [ ] `shadow_reconstruction_benchmark.py` (or equivalent) CLI in `packages/evaluation`
- [ ] Alex fixture population script through ingest + decay stages
- [ ] Strip step: remove keys, identity mappings, credentials, PRIVATE_RAW cache
- [ ] Reconstructability scorer (analyst rubric + automated checks where possible)
- [ ] Utility scorer: attention fidelity, open-loop fidelity, dependency fidelity, next-action fitness
- [ ] PASS/FAIL report artifact with per-metric scores, target-curve assessment, and explicit Reconstructability-dimension verdict for SEC-05 Q16
- [ ] CI integration: benchmark runs on Alex fixture after SEC-06 decay pipeline changes

## Acceptance criteria

- [ ] Benchmark runs end-to-end on Alex fixture without manual steps
- [ ] Reconstructability metrics all **0** on current shadow schema (or documents known FAIL with ticket link)
- [ ] Utility metrics ≥ configured thresholds on current shadow schema
- [ ] Report emitted in format consumable by SEC-05 gate runner (Q16 evidence)
- [ ] Target curve assessment included in report output — explicit statement whether biographical detail collapsed faster than utility
- [ ] Detective-novel criterion scored: stripped shadow is useful-and-boring, not a recognisable life
- [ ] Evaluators score reconstructability as outsiders (no `ALEX_BIOGRAPHY.md`; fixtures are source of truth)

## Test plan

- Unit: strip step removes keys/mappings/raw cache; shadow rows remain
- Unit: reconstructability scorer detects injected name in fixture → FAIL
- Unit: exact leakage — grep `reconstructability_probe_sentinels()` in shadow export → **0**
- Unit: semantic leakage — `SemanticLeakageScorer` stub (`@pytest.mark.skip` until shadow runner)
- Integration: full benchmark on Alex → report with all metric scores
- Regression: utility thresholds tied to attention fixture gold labels
- **Canary dependency:** populate canary pack into Alex fixture DB; after strip, `reconstructability_probe_sentinels()` must all score **0** (`alex_security_canaries.py`)

## Privacy constraints

- Benchmark artifacts must not contain real mail bodies or live tokens
- Stripped DB export used for scoring must not leave CI artifacts unencrypted
- Do not emit `ALEX_BIOGRAPHY.md` or any compiled-life artifact from the benchmark — fixtures remain the source of truth

**Unlocks:** SEC-05 Q16 evidence → Reconstructability PASS

## Related ADR

[ADR-023](../../docs/adr/023-persistent-shadow-abstract-state-not-biography.md) · [data-retention.md](../../docs/architecture/data-retention.md) · [ethics.md](../../docs/architecture/ethics.md) · [ADR-026](../../docs/adr/026-ethics-creed-user-is-subject.md) · [SEC-06](./SEC-06-retention-memory-decay-forget.md) · [SEC-05 Q16](./SEC-05-personal-data-pilot-gate.md)

## UI observability (C10)

The [Cortex visualizer](../../docs/architecture/cortex-visualizer.md) ([C10](../conversational-ui/C10-cortex-brain-visualizer.md)) exposes a **SOURCE → ACTIVE → SHADOW → FORGOTTEN** slider with utility % vs reconstructability % — stub metrics until this benchmark emits live scores. Privacy mode on the membrane region links to egress disclosure rows ([SEC-02](./SEC-02-audited-remote-egress-gate.md)).
