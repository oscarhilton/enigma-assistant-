# Attention surface — Phase 2.5 wind-tunnel finding

**Status:** Design note from a live Demo Attention dump (alex-v1 / D14). Not an implementation ticket.  
**Related:** [M06](../../tickets/attention/M06-attention-engine.md) · [D08c–e](./demo-corpus.md) · [shadow-mode-questions.md](./shadow-mode-questions.md)

## Successful failure

Demo Mode’s job before Shadow is to make Enigma look slightly ridiculous in ways we can name and regress. A live Attention dump did exactly that:

| Observed | Intended product |
| --- | --- |
| ~40 signals → **11** chatty cards (~27.5% surface rate) | ~40 signals → **~2** high-value items |
| Calendar existence treated as obligation | Scheduled existence ≠ obligation |
| Past events labeled “Deadline approaching” | Explicit deadline states via injected clock |
| Machine sludge merged into one “commitment” | Early gate + pollution traces |
| Open threads → `INFERRED_COMMITMENT` @ 0.55 | `PENDING_REPLY` / open-loop vs real commitment |

The top two cards were already right. Everything below them is the product thesis failing in measurable ways: Enigma currently understands “this might be a thing” better than “this is worth interrupting a human about.”

## Target surface (same simulated moment)

**Must surface (HIGH):**

1. Book Saturday brunch for Elena's parents — explicit reminder + supporting mail/calendar + concrete deadline  
2. Draft colour + spacing token inventory — multi-source convergence + approaching deadline  

**Optional, lower priority:** Quick sync next week? as `PENDING_REPLY` — not `INFERRED_COMMITMENT` @ 0.55  

**Must not surface as Attention cards:**

- Bare calendar: Team standup, 1:1 Maya, Dentist → situational / upcoming context  
- Machine / promo / newsletter / package noise: PrizeVault, Design Weekly, RouteFox, BuildCloud, SyncForge, ProductPulse, GrowthKit, PromoNest, …  
- Distinct social plans wrongly merged (e.g. Dinner Thursday? + Climbing Sunday?)  

Compression picture:

```text
40 signals observed
        ↓
2 genuinely useful attention items
(+ maybe 1 pending-reply)
```

not `40 → 11`.

## Product rules

### 1. Calendar existence ≠ obligation

Hard rule: **scheduled existence is not an obligation.**

A calendar event may *evidence* an obligation; it should rarely *be* the Attention item. Bare events belong in a situational / upcoming model unless exceptional (starting soon + prep/travel, changed, cancelled, conflict, explicit action, likely miss).

Canonical pattern:

```text
Commitment: Review Atlas proposal
     +
Calendar: Atlas review Friday
        ↓
Attention: Review Atlas proposal before Friday
```

### 2. Deadline states (clock-aware)

Do not collapse everything inside an attention window into “Deadline approaching.” Distinguish at least:

| State | Intent |
| --- | --- |
| `APPROACHING` | Within attention window, not imminent |
| `DUE_SOON` / `DUE_TODAY` | Tight timing |
| `OVERDUE` | Past due, still actionable |
| `STALE` | Past beyond stale threshold — usually resolve / drop |

Past calendar events should normally resolve and disappear, not linger forever as overdue obligations. The January 5 Team standup (when “now” is ~Jan 21/22) is the regression canary for this.

### 3. Machine mail early gate

Knock newsletters, marketing, promo, and automated notifications out **before** expensive commitment reasoning (D08d). Prefer a pragmatic `MESSAGE_ORIGIN`-style gate (`HUMAN` vs `NEWSLETTER` / `MARKETING` / `AUTOMATED_*`) from local headers and sender patterns. Marketing/newsletters never create commitments by themselves; automated notifications only under narrow actionable rules.

### 4. `PENDING_REPLY` vs `COMMITMENT`

Repeated confidence **0.55** on open threads is a diagnostic smell (likely fallback). An unanswered question or social proposal is not a user commitment.

- **Commitment** needs evidence the user undertook/accepted an action (“I'll…”, accepted request, explicit task/reminder, …).  
- **Pending reply / open request** is coordination: may surface later when relationship importance + unreplied age + proposed date warrant it.

### 5. Surface threshold (not `confidence ≥ 0.5`)

Pipeline shape:

```text
CANDIDATES (all open loops)
        ↓
ATTENTION POLICY → suppress | remember/dormant | contextual | surface
```

Rough priority policy for the default interrupt surface:

| Priority | Default |
| --- | --- |
| 5–4 | Surface |
| 3 | Surface if timing warrants |
| 2 | Open loop / dormant — do not interrupt |
| 1 | Context only |
| 0 | Discard |

Cap the default view: “what actually needs your attention” should not dump every legitimate open loop. Prefer “N things need your attention” + optional “Show K that can wait.”

### Demo attention surface shape (frozen)

The live Demo Attention surface copy/layout is **frozen** for polish as three levels:

```text
WORLD MODEL
  ├─ ATTENTION   — NEEDS YOU (may be empty)
  ├─ NEXT ACTION — WORTH DOING (never empty; always optional)
  └─ CAN WAIT    — secondary, grouped counts
```

- Headline: “Nothing needs you right now” / “N things need your attention”
- Empty silence is an active decision — no Refresh CTA, no celebration empty states; offer one optional Next Action (must include rest / do nothing among cycle options)
- Walk / junk / rest are **never** HIGH PRIORITY Attention cards
- Expanded can-wait is secondary category counts, not a mini Attention list
- Card face: title + compact badges + one natural reason sentence + Why?/Done/Snooze
- **Done / Snooze / I’ll do that are Demo / Assisted only** — Shadow must not show intervening actions
- Reliability of *which* two cards surface is the next hard problem, not more card chrome

### 6. Card UX vs Why

User-facing cards: title, compact priority/due, one short natural reason, actions.  
Evidence dumps (`Reminder: …; Email: …; Calendar: …`) belong in **Why**, not the card body. Debug/eval dashboards are fine in the lab; they must not become the product Attention design.

## PrizeVault as pollution canary

`Congrats — claim your PrizeVault reward` as a single `INFERRED_COMMITMENT` bundling PrizeVault, LoginShield, MeetSlot, ProductPulse, SlotKeeper, GrowthKit, PromoNest, BuildCloud, SyncForge, … is not one misclassification — it is **retrieval / context-boundary pollution**.

This is exactly what [D08c pollution traces](./demo-corpus.md) were designed to catch. Inspect first: embedding neighbourhood, synthetic contact, thread, shared “action” language, temporal proximity, fallback retrieval. Unrelated machine mail must not share one obligation fingerprint.

## Named F-* regression fixtures

These came from the wind tunnel (not invented edge cases):

| Fixture | Guards |
| --- | --- |
| `F-calendar-existence-is-not-attention` | Bare calendar ≠ AttentionItem |
| `F-past-calendar-event-resolves` | Past events resolve; no immortal overdue |
| `F-automated-mail-is-not-commitment` | Automated / promo mail ≠ commitment |
| `F-newsletter-is-not-commitment` | Newsletter alone ≠ commitment |
| `F-package-notification-is-not-commitment` | Package trackers ≠ commitment |
| `F-social-question-is-pending-reply` | Questions → pending reply, not commitment |
| `F-unrelated-machine-mail-not-merged` | PrizeVault-style cluster must not merge |
| `F-distinct-social-plans-not-merged` | Dinner vs climbing stay distinct |
| `F-low-priority-candidate-not-surfaced` | P2 stays candidate, not interrupt |

Claim / land these in the order documented in [tickets/README.md](../../tickets/README.md) (alongside existing F-background-* / F-corpus-* waves). Do not invent D08f for this — new abstractions earn existence by explaining these measured failures.

## Why this matters for Phase 2.5 → Shadow

Phase 2.5 exit is not “the simulator looks busy.” It is compression + false-alert discipline under realistic noise ([demo-corpus.md](./demo-corpus.md#phase-25-exit--shadow-mode)). This dump is the qualitative twin of quiet-day / false-alert metrics: until brunch + token inventory (and not PrizeVault / Dentist / Design Weekly) are the default story, Shadow would mostly teach us the same lesson again at higher cost.
