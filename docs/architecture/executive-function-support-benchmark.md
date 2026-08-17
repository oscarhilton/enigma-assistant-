# Executive-function support benchmark

**Status:** Design capture (Phase 2.5 / Alex v2)  
**Governing ADR:** [011-observable-support-challenges-only.md](../adr/011-observable-support-challenges-only.md)  
**Schema stub:** [eval-stubs/support_contract.v0.json](./eval-stubs/support_contract.v0.json)

## Core insight

The Alex v1 benchmark mostly asks:

> **Did Enigma correctly understand what matters?**

Product also needs a second, independent dimension:

> **Given what matters, did Enigma offer help that reduces executive-function friction?**

These are different abilities. A system can surface the right obligation on time yet suggest “DO EXPENSES NOW” — correct attention, poor support. Conversely, a charming micro-step is useless if it targets the wrong open loop.

**Do not label datasets `ADHD=true`.** Encode observable executive-function *situations* via evaluator-only `support_challenges` tags. Persona files may keep behavioural ground truth for authors (`admin_avoidance: moderate` in [`scenarios/alex-v1/persona.yaml`](../../scenarios/alex-v1/persona.yaml)) — that is author-side, not handed to Enigma.

---

## Three headline benchmark families

| Family | Question | Primary metrics (existing + new) |
| --- | --- | --- |
| **World-model accuracy** | Did Enigma understand the situation? | Obligation recall, commitment merge, memory checkpoints ([D06](../../tickets/demo-evaluation/D06-ground-truth.md)) |
| **Attention accuracy** | Did it speak / stay quiet at the right time? | Critical recall, precision, stale alerts, suppression ([D07](../../tickets/demo-evaluation/D07-evaluation-runner.md), [demo-corpus.md](./demo-corpus.md)) |
| **Support fitness** | Did it suggest something the person could actually do? | Actionability, task-size fit, friction reduction, timing fit, context fit, repetition penalty, user-preference fit (future / Shadow), non-nagging |

Support fitness is **new eval surface area** — tracked by [EF-01](../../tickets/demo-evaluation/EF-01-support-fitness-evaluator.md) and scenario contracts in Alex v2.

---

## Support challenge vocabulary

### Alex v1 retrospective tags

Used when mapping existing scenarios; v1 ground truth does not yet include these fields.

| Tag | Meaning |
| --- | --- |
| `prospective_memory` | Future intention must be held across delay / sources |
| `task_initiation` | Known task; starting is the bottleneck |
| `ambiguity` | Unclear scope or decision frame |
| `transition_cost` | Switching contexts is expensive |
| `working_memory` | Holding multiple threads without dropping one |
| `time_estimation` | Misjudging how long something takes |
| `distraction` | Competing low-value signals |
| `admin_friction` | Bureaucratic / form-filling aversion |

### Alex v2 extended set

Additional tags for deliberately authored arcs (~30 across a 12-month Alex):

| Tag | Meaning |
| --- | --- |
| `task_decomposition` | Giant vague task needs a first slice |
| `time_blindness` | Now vs next commitment horizon mismatch |
| `transition` | Imminent calendar boundary |
| `interruption_recovery` | Resume after disruption |
| `blocked_task` | External dependency is the real next step |
| `recurrence` | Repeating admin drift over months |
| `energy_mismatch` | Suggestion effort vs likely capacity |
| `social_coordination` | Low-urgency relationship maintenance |
| `overwhelm` | Too many parallel threads |

Full enum lives in [support_contract.v0.json](./eval-stubs/support_contract.v0.json).

---

## Evaluator-only support contract

Alongside scenario truth (obligations, attention windows, memory checkpoints), authors declare **what good help looks like** at scored instants. Enigma never sees this.

### Example (December expenses)

```yaml
scenario: december-expenses
obligation_id: obligation_december_expenses
challenge:
  - admin_friction
  - task_initiation
attention:
  behaviour: MUST_SURFACE
  window:
    start: 2026-01-14T09:00:00Z
    end: 2026-01-16T10:00:00Z
  minimum_priority: 3
support:
  good_next_actions:
    - gather_receipts
    - open_expenses_form
    - submit_if_ready
  poor_actions:
    - restate_deadline_only
    - surface_repeatedly
    - manufacture_urgency
  preferred_effort:
    max_minutes: 10
    effort: light
```

On-disk home: `scenarios/alex-v1/ground_truth/support_contracts.yaml` (v0.2.1 January exists; Feb–Jun overlay after [D08f](../../tickets/demo-scenario/D08f-alex-six-month.md)). Do **not** create `scenarios/alex-v2/`.

### Support fitness metric rubric

| Metric | Pass signal | Fail signal |
| --- | --- | --- |
| **Actionability** | Concrete verb + object (“gather receipts”) | Vague nag (“don’t forget expenses”) |
| **Task size fit** | ≤ `preferred_effort.max_minutes` | Whole-project framing |
| **Friction reduction** | Lowers activation energy | Restates deadline or guilt |
| **Timing fit** | Surfaces inside attention window when user could act | Too early, too late, or during blocked slot |
| **Context fit** | Matches calendar / location / tool availability | Suggests deep work minutes before meeting |
| **Repetition penalty** | Surfaces once per open loop until state change | Re-nags after dismiss or completion |
| **User preference fit** | Respects known avoidance patterns (Shadow / future) | Phone call when user avoids calls |
| **Non-nagging** | Calm, proportional tone | Manufactured urgency |

---

## Alex v1 — accidental EF coverage (mapping)

Alex v1 ([`scenarios/alex-v1/`](../../scenarios/alex-v1/)) was authored for world-model + attention. Several arcs already exercise support fitness **implicitly**. This table is the retrospective catalogue; it does not mutate the immutable v1 package.

| Scenario arc | Evidence ids (sample) | `support_challenges` | Better Enigma aid |
| --- | --- | --- | --- |
| Q1 priorities due Friday | `obligation_q1_roadmap`, `mail-maya-q1`, `rem-q1-roadmap` | `prospective_memory`, `ambiguity` | Surface at useful time; concrete first step (“pick three priorities”) not “send roadmap” |
| Dinner with Elena / buy wine | `mail-elena-dinner`, `rem-buy-wine`, `cal-dinner-elena` | `prospective_memory` | Timed reminder when practical (e.g. Thursday afternoon), not morning of |
| Checkout Q1 decision | `obligation_checkout_rec`, `note-checkout-ambig` | `ambiguity` | Reduce to “make recommendation” with 2-option frame; not “resolve checkout redesign” |
| December expenses | `mail-finance-expense`, `rem-expenses` | `admin_friction`, `task_initiation` | “Spend 5 min gathering receipts” not “DO EXPENSES” |
| Token inventory | `obligation_token_audit`, `mail-jordan-figma`, `note-token-wip` | `blocked_task`, `working_memory` | Notice Jordan’s Figma link is actual next action |
| Dentist + overlapping critique | `cal-dentist`, `cal-crit-overlap`, `cal-dentist-cancel` | `transition`, `transition_cost` | Resolve conflict; disappear once cancelled |
| Elena’s parents / brunch | `mail-elena-weekend`, `rem-brunch-book`, `cal-brunch-parents` | `prospective_memory`, `social_coordination` | Suggest book restaurant, not repeat event details |
| Sam empty-state reply | `obligation_empty_states`, `note-open-loop-sam` | `task_initiation`, `working_memory` | Tiny reply action at suitable moment; avoid stale re-alerts |
| Climbing / dinner social | `mail-tom-climb`, `cal-climb-tom` | `social_coordination`, `low_urgency`* | Keep warm without fake urgency |
| Newsletters / promos | `mail-noise-designweekly`, `noise-newsletter-*`, `mail-noise-saas` | `distraction` | Ruthlessly suppress |
| Quiet periods | `note-weekend-w1`, sparse calendar gaps | `task_initiation`* | Offer walk / rest / admin micro-task / small useful task — not “you have nothing to do” |

\*`low_urgency` is author shorthand here; prefer `social_coordination` + explicit `MUST_SUPPRESS` attention behaviour in v2 contracts.

### Illustrative checkpoint — attention ≠ next action

**2026-01-21 13:30 UTC** (token review day):

| Checkpoint | Expected |
| --- | --- |
| **Attention** — “What needs me?” | Book Saturday brunch (Elena parents) — social coordination still open |
| **Next action** — “What should I do next?” | Prepare token review draft in ~30 min — meeting at 14:00 |

These differ by design. They validate the three-level attention model:

```text
NEEDS YOU  →  WORTH DOING  →  CAN WAIT
```

Attention ranking ([`packages/attention`](../../packages/attention/src/personal_enigma/attention/engine.py)) handles **what needs me**. Support fitness scores **what should I do next** — a separate product surface (Contextual Next Action; see [Three squeezes](#three-squeezes-progression) below).

---

## Alex v2 — deliberate EF arcs

Alex v2 spans ~12 months with **~30 authored arcs** targeting **8 EF patterns** ([V2-EF-02](../../tickets/demo-scenario/V2-EF-02-ef-arc-authoring.md)):

| # | Pattern | Example arc shape |
| --- | --- | --- |
| 1 | Knows what to do, doesn’t start | Open reminder + repeated deferral; good aid = 2-minute entry action |
| 2 | Ambiguous giant task | “Improve onboarding” with no owner; good aid = scoped recommendation |
| 3 | Hyperfocus / wrong-task persistence | Deep note thread while calendar obligation approaches |
| 4 | Interruption and resumption | Mid-task mail burst; good aid = resume pointer not full recap |
| 5 | Time blindness / transition | 14:35 now, meeting 15:00; bad aid = quarterly strategy; good = 20-min prep |
| 6 | Boring recurring admin (12 mo) | Expenses / timesheet drift; learn pattern without shaming |
| 7 | Working-memory disappearance | Obligation + 50 unrelated items + 8 days silence |
| 8 | Avoided communication | Phone-call avoidance; good aid = online booking link discovery |

Each arc ships: timeline events + obligation/window truth + **support contract** + at least one checkpoint where attention and next_action diverge.

---

## Two independent checkpoint questions

At every scored checkpoint the evaluator asks:

1. **WHAT NEEDS ME?** (Attention family) — surface, suppress, timing, priority band.
2. **WHAT SHOULD I DO NEXT?** (Support fitness) — title, estimated minutes, effort, `why_this_now`.

Structured LLM benchmark output (Arm B/C) should return both without chain-of-thought:

```json
{
  "attention": {
    "item_id": "obligation_token_audit",
    "behaviour": "surface",
    "priority": 4
  },
  "next_action": {
    "title": "Open Jordan's Figma link and note three spacing gaps",
    "estimated_minutes": 15,
    "effort": "light",
    "why_this_now": "Review in 45 minutes; link unblocks draft"
  }
}
```

Deterministic scorer matches `next_action` against `good_next_actions` / `poor_actions` tokens and rubric fields. See [D14 LLM judge benchmark](../../tickets/demo-evaluation/D14-llm-judge-benchmark.md).

---

## Pipeline cross-link (no duplication)

Enigma’s runtime path (MVP + Demo):

```text
sources → domain → identity/dedupe → merge
    → obligations/commitments → attention candidates
    → heuristic ranking → NEEDS YOU / WORTH DOING / CAN WAIT
```

| Stage | Doc / ticket |
| --- | --- |
| Architecture overview | [overview.md](./overview.md) |
| Obligations + commitments | [M15](../../tickets/obligations/M15-cross-source-merging.md), [M16](../../tickets/obligations/M16-commitment-tracking.md) |
| Attention engine | [M06](../../tickets/attention/M06-attention-engine.md) |
| Ground truth + signal class | [D06](../../tickets/demo-evaluation/D06-ground-truth.md) |
| Eval runner + suppression | [D07](../../tickets/demo-evaluation/D07-evaluation-runner.md) |
| Demo corpus / noise | [demo-corpus.md](./demo-corpus.md) |
| Shadow open questions | [shadow-mode-questions.md](./shadow-mode-questions.md) |
| Representation layers | [representation-layers.md](../demo/representation-layers.md) |

**Support fitness** sits **after** attention ranking in evaluation — it judges the *quality of suggested help*, not whether the obligation was detected. Runtime Next Action generation is future work (fourth squeeze); this benchmark defines acceptance criteria before implementation.

---

## Three squeezes progression

Documented product/eval maturity path:

| Squeeze | Question | Benchmark hook |
| --- | --- | --- |
| **1 — Reasoning LLM** | “What does this mean?” at the transformation boundary | World-model + obligation merge (M03, M15–M16) |
| **2 — Longitudinal memory** | “What still matters across months?” | Six-month ordinary events in `alex-v1` ([D08f](../../tickets/demo-scenario/D08f-alex-six-month.md)); V2-EF-02 support contracts on those threads |
| **3 — Shadow Mode** | “Does real behaviour match synthetic?” | [shadow-mode-questions.md](./shadow-mode-questions.md); preference fit metric |
| **4 — Contextual Next Action** *(secret fourth)* | “What should I do next, right now?” | Support contracts + EF-01 evaluator; structured LLM arm |

Phase 2.5 exit ([demo-corpus.md](./demo-corpus.md#phase-25-exit--shadow-mode)) proves squeezes 1–2 on synthetic Alex. Support fitness extends the laboratory before Shadow.

---

## Implementation tickets

| Ticket | Scope |
| --- | --- |
| [V2-EF-01](../../tickets/demo-scenario/V2-EF-01-support-contract-design.md) | Schema freeze, loader validation, v1 catalogue YAML |
| [V2-EF-02](../../tickets/demo-scenario/V2-EF-02-ef-arc-authoring.md) | Support contracts on D08f Jan–Jun threads (not `alex-v2`) |
| [EF-01](../../tickets/demo-evaluation/EF-01-support-fitness-evaluator.md) | D07 extension: support fitness metrics + checkpoint scorer |
| [D14](../../tickets/demo-evaluation/D14-llm-judge-benchmark.md) | LLM arms: structured `attention` + `next_action` scoring |

---

## Privacy and invariants

- Support contracts and `support_challenges` are **evaluator-only** — same bar as [ADR-011](../adr/011-observable-support-challenges-only.md) and D06 signal classes.
- Never send persona traits, challenge tags, or `poor_actions` lists to hosted models during Private Mode operation.
- Demo Mode never shares Private storage roots ([ADR-005](../adr/005-demo-private-storage-roots.md)).

---

## Open questions

1. **Exact match vs semantic similarity** for `next_action.title` — start deterministic token/id match; optional embedding threshold behind flag?
2. **Repetition penalty** — per obligation id, per attention item, or per support contract window?
3. **Preference fit before Shadow** — stub as “author-declared avoidance” in contract only, or defer metric until Shadow data exists?
4. **Runtime Next Action API** — separate ticket once EF-01 proves eval rubric on synthetic arcs.
