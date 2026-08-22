# Next Action — worth doing without faking urgency

**Status:** Foundational product model (design + thin domain stub)  
**Principle:** Enigma always has something useful to offer, and never pretends something is urgent when it isn’t.  
**Related:** [attention-surface.md](./attention-surface.md) · [ADR-010](../adr/010-next-action-not-attention.md) · [shadow-mode.md](./shadow-mode.md) · silence audit (soft) [shadow-silence-evaluation.md](./shadow-silence-evaluation.md)  
**Tickets:** [M20](../../tickets/domain-model/M20-next-action-schemas.md) · [N01](../../tickets/next-action/N01-scorer-stub.md)–[N03](../../tickets/next-action/N03-preference-learning.md) · Demo chrome [D18](../../tickets/demo-ui/D18-demo-next-action.md)

## Objective

Help the user choose a **good next use of their attention**.

That is not maximum task throughput. Sometimes the good next use is work; sometimes maintenance, preparation, play, movement, or **nothing**.

```text
WORLD MODEL
    │
    ├──────────────► ATTENTION          NEEDS YOU
    │                Things requiring you
    │                may be EMPTY
    │
    ├──────────────► NEXT ACTION        WORTH DOING
    │                One useful thing you could do
    │                NEVER empty · optional=true
    │
    └──────────────► CAN WAIT           remembered / dormant
                     Known, deliberately not interrupting
```

## Three levels

| Level | Product name | Output | Empty? | Urgency implied? |
| --- | --- | --- | --- | --- |
| 1 | **NEEDS YOU** | `AttentionItem` list | Yes — legitimate silence | Yes (interruption-worthy) |
| 2 | **WORTH DOING** | single `NextAction` | **Never** | No — optional by default |
| 3 | **CAN WAIT** | suppressed / dormant candidates | Count may be > 0 | No |

Attention answers: *“What may go wrong if ignored?”*  
Next Action answers: *“Given everything you know, what would be a good thing for me to do now?”*  
Can Wait answers: *“What do we remember but refuse to interrupt about?”*

Do **not** shoehorn walks, junk-mail tidy-ups, or rest into Attention. That manufactures crisis.

## `NextAction` (not `AttentionItem`)

Canonical types live in `packages/domain` ([M20](../../tickets/domain-model/M20-next-action-schemas.md)). Sketch:

```python
class NextAction:
    title: str
    reason: str

    category: ActionCategory

    estimated_minutes: int | None
    effort: Effort
    context: list[ActionContext]

    source_ids: list[str]

    urgency: Urgency
    value: float
    confidence: float

    optional: bool = True
```

### Categories (`ActionCategory`)

`OBLIGATION` · `OPEN_LOOP` · `MAINTENANCE` · `ADMIN` · `COMMUNICATION` · `PREPARATION` · `CREATIVE` · `LEARNING` · `MOVEMENT` · `REST` · `SOCIAL` · `HOUSEHOLD` · `NOTHING`

`NOTHING` / `REST` are first-class. Example when obligations are under control:

> Put some music on and do absolutely nothing for twenty minutes.

### Scoring sketch (not highest-priority-wins)

Approximate fitness:

```text
score ≈ usefulness
      × actionability
      × contextual_fit
      × current_capacity
      × time_fit
      × novelty_repetition_penalty
```

**Urgency multiplies only when urgency exists.** A walk does not become Priority 5; it wins when it is the best fit for time, load, and capacity.

Illustrative moment:

| Belief | Value |
| --- | --- |
| time_available | 25 min |
| attention_load | high |
| energy | uncertain |
| next_meeting | 40 min |
| critical_open_loops | 0 |
| admin_backlog | moderate |
| recent_sitting | long |

| Candidate | value | effort | Likely pick? |
| --- | --- | --- | --- |
| Clean inbox | 0.45 | low | maybe later |
| Write project proposal | 0.80 | high | poor capacity fit |
| Go for walk | 0.70 | low | **yes** |
| Read article | 0.35 | medium | weak |

## UX contracts

### Always offer Something else

Rejection is a **learning signal**, not a permanent hate list.

```text
Go for a walk
        ↓ Something else
Clear 14 junk emails
        ↓ Something else
Message Tom back
        ↓ Something else
Do nothing for a bit
```

Cautious preference memory (see [N03](../../tickets/next-action/N03-preference-learning.md)):

> When no urgent work exists and cognitive load is high,  
> maintenance/admin suggestions have historically had low acceptance.

Not: “Oscar hates email cleaning.”

### Anti–productivity treadmill

“Always suggest something” must not become “GOOD NEWS! HERE IS ANOTHER TASK!”  
Legitimate recommendations include rest, nothing, and “you don’t need to optimise this gap.”

### Demo layouts (frozen product shape)

**Attention non-empty**

```text
2 things need you

Review Atlas proposal
Follow up with Maya

─────────────────────
NEXT
Review the Atlas proposal · ~20 min
─────────────────────
47 things can wait
```

NEXT is derived from a surfaced Attention item when that is the sensible next use — **not** a second Attention card.

**Attention empty**

```text
Nothing needs you right now.

NEXT / YOU COULD
Go for a short walk · ~15 min
You've got a clear hour before your next commitment.

[Let's do it] [Something else]

─────────────────────
47 things can wait
```

Demo UI ticket: [D18](../../tickets/demo-ui/D18-demo-next-action.md) (chrome only; model ownership stays here / M20 / N*).

## Relationship to Attention freeze

[attention-surface.md](./attention-surface.md) freezes interrupt discipline (compression, calendar ≠ obligation, Done/Snooze Demo-only). This doc freezes the **companion** output: optional Next Action that fills the executive-function gap between “needs you” and “can wait.”

## Relationship to Polaris search (later, gated)

[polaris-search.md](./polaris-search.md) proposes a receding-horizon planner for **WORTH DOING**. It does not replace this three-level surface, N01’s local fitness stub, or Attention policy.

- Search may look many plies ahead; product output remains **one optional next action** (or REST / NOTHING).
- Promotion onto the live Next Action path is [POLARIS-SEARCH-07](../../tickets/polaris/POLARIS-SEARCH-07-controlled-promotion.md), after Alex life-position benchmarks and shadow comparison.
- Until then the current scorer (or Demo stubs) remains user-visible ([POLARIS-SEARCH-06](../../tickets/polaris/POLARIS-SEARCH-06-shadow-mode.md)).

Do not fold search trees into `AttentionItem`. Do not treat a principal variation as a committed plan.

## Shadow (later, soft)

Shadow audits **silence** ([shadow-silence-evaluation.md](./shadow-silence-evaluation.md) · [shadow-evaluation.md](./shadow-evaluation.md)): Done/Snooze intervening actions stay Demo/Assisted.

Next Action may still exist in Shadow as an **observation** of what would have been suggested — not as a notification, and not as proof that Attention silence was correct. Silence evaluation and Next Action recommendation are related but separate claims.

## Package boundaries

| Concern | Home |
| --- | --- |
| `NextAction` + enums | `packages/domain` (M20) |
| Scorer / ranking stub | `packages/attention` or successor package (N01) — must not widen `AttentionItem` |
| Receding-horizon planner | Polaris tickets (`future`) — local eval + search; not a global life score ([ADR-046](../adr/046-local-evaluation-under-uncertainty.md)) |
| Something-else cycle API | Core + Demo (N02); Demo chrome D18 |
| Preference memory | Private-local cautious stats (N03); never remote raw rejects with PII |
| Demo surface stubs | `apps/web` / demo API (D18) |

Provider payloads stop at ingestion. Next Action reasons about domain concepts and attention candidates, not `EKEvent` shapes.
