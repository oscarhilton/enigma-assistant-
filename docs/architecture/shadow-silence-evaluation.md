# Shadow silence evaluation

**Status:** Design + ticket scaffold — not a full Shadow product build  
**Core principle:** Every silence is a prediction. Empty screen alone cannot prove correctness.  
**Mode scaffold:** [shadow-mode.md](./shadow-mode.md) · storage [ADR-008](../adr/008-shadow-storage-roots.md)  
**Rubric (seven questions):** [shadow-evaluation.md](./shadow-evaluation.md) · [shadow-mode-questions.md](./shadow-mode-questions.md)  
**Decision ADR:** [ADR-009](../adr/009-silence-as-prediction.md)  
**Open loops / commitments:** [open-loop-commitments.md](./open-loop-commitments.md)  
**Tickets:** [SE04](../../tickets/shadow/SE04-suppression-decision-log.md)–[SE11](../../tickets/shadow/SE11-open-loop-due-resolution.md) (soft on S01–S06 / SE01–SE03)

## Why silence needs its own evaluation track

Shadow Mode suppresses notifications and can leave the attention surface empty. That emptiness is not evidence that Enigma was right — it is only evidence that Enigma **chose not to speak**.

The product claim we must eventually defend is not “the UI was quiet,” but:

> Given what was knowable then, suppressing this candidate was the correct prediction.

Demo Mode can score against authored ground truth. Shadow has a real life: behavioural traces, stratified human audits, and explicit miss reports. Those three channels combine; none alone is ground truth.

```text
EMPTY SCREEN  ≠  CORRECT SILENCE

Correct silence requires:
  1. Logged prediction (frozen SUPPRESS snapshot)
  2. Later evidence channels that can falsify it
  3. Metrics that treat important misses as first-class failures
```

## Three evidence channels

### 1. Post-suppression behavioural traces (signals, not truth)

For **every** attention candidate — including `SUPPRESS` — write a private evaluation record under the Shadow root. Later behavioural events can nominate a candidate for **suppression review** without auto-failing the decision.

Examples of mismatch signals (non-exhaustive):

| Later signal | Why it might matter |
| --- | --- |
| User reply like “Sorry meant to get back…” on a suppressed thread | Possible pending-reply miss |
| Calendar edit near a suppressed event | Possible time-sensitive miss |
| Reminder created that derives from a suppressed message | Possible capture miss |
| User opens / stars / forwards the suppressed subject soon after | Possible under-attention |

**Rule:** behavioural mismatch → review candidate, **not** automatic `FALSE_NEGATIVE`. Humans (or a later adjudication step) decide. This keeps SE01-style action joins and silence audits honest about uncertainty.

Ticket: [SE05](../../tickets/shadow/SE05-behavioural-mismatch-stubs.md) (stubs); records feed [SE04](../../tickets/shadow/SE04-suppression-decision-log.md).

### 2. Stratified sampling audits (3–5/day initially)

Quiet UX prompt (private Shadow accuracy surface — **not** Demo chrome):

> Enigma decided these did not need your attention. Was that right?

Labels:

- **Should have surfaced**
- **Fine to suppress**
- **Unsure**

**Stratify** the daily sample (do not draw only from easy machine noise):

| Stratum | Intent |
| --- | --- |
| Near-threshold | Borderline priority vs suppress threshold |
| Very low-score | Sanity-check that deep noise stays quiet |
| Human requests | Messages that ask the user for something |
| Calendar-derived | Time-bound candidates |
| Machine mail | Newsletters, receipts, automated systems |
| Uncertain | High model/heuristic uncertainty |

**Active learning:** reduce sampling on strata that are consistently “Fine to suppress” (especially machine noise); concentrate budget on borderline, ambiguous, relationship-sensitive, and time-sensitive items.

Ticket: [SE06](../../tickets/shadow/SE06-stratified-sample-queue.md).

### 3. Reported misses (gold-standard)

Periodic prompt:

> Did anything need your attention that Enigma failed to identify?

The user may point at email / calendar / reminder / person, or describe the miss in free text. Intake reconstructs **what Enigma knew then** (frozen retrieval + candidate state), labels a **FALSE NEGATIVE**, and records **failure stage**:

| Stage | Meaning |
| --- | --- |
| `retrieval` | Relevant evidence never entered the candidate set |
| `entity` | Wrong PERSON_* / merge / identity binding |
| `reasoning` | Evidence present; interpretation wrong |
| `surface_threshold` | Ranked correctly as low; threshold / policy silenced it |

Ticket: [SE07](../../tickets/shadow/SE07-miss-report-intake.md).

## Frozen decision snapshots

Every `SUPPRESS` (and preferably every surface decision) persists a **frozen snapshot** so later review replays original evidence — **no hindsight cheating**.

```json
{
  "decision": "SUPPRESS",
  "decided_at": "2026-08-16T09:00:00Z",
  "candidate": "cand_pending_reply_42",
  "available_evidence": ["msg_ref_a", "cal_ref_b"],
  "retrieval_snapshot": ["chunk_ref_1", "chunk_ref_2"],
  "priority": 2,
  "confidence": 0.67,
  "threshold": 3,
  "reason_codes": ["PENDING_REPLY", "LOW_URGENCY"]
}
```

Distinguish:

| Verdict family | Meaning |
| --- | --- |
| Wrong given what was knowable then | Replay of the frozen snapshot fails human / gold judgement |
| Something eventually involved that email | New evidence arrived later; morning silence may still have been correct |

Ticket: [SE04](../../tickets/shadow/SE04-suppression-decision-log.md). Stub shape: [shadow-eval-stubs/suppression_decision.v0.json](./shadow-eval-stubs/suppression_decision.v0.json).

## Day-freeze retrospective

Morning summary form (illustrative):

> Nothing needs you · 47 can wait

Evening classification of the frozen set (the 47), per item or in batches:

| Class | Meaning |
| --- | --- |
| Irrelevant | Correctly dormant noise |
| No follow-up | Correct silence; nothing happened |
| Became relevant from **new** info | Morning silence OK; afternoon evidence changed the world |
| User handled dormant correctly | User acted without Enigma; silence may still be fine |
| Should have surfaced at 09:00 | Silent miss relative to morning freeze |

Day freeze is a structured retrospective over **logged predictions**, not a vibe check on whether the day felt calm.

## Headline Shadow metrics

Human-facing names for silence quality (implement in [SE08](../../tickets/shadow/SE08-silence-metrics.md)):

| Metric | Definition | Direction |
| --- | --- | --- |
| **Suppression Accuracy** (silence precision) | `correctly_suppressed / suppressed_items_audited` | High |
| **Silent Miss Rate** | `important_missed / important_discovered_during_evaluation` | Extremely low |

“Audited” includes stratified labels + adjudicated behavioural reviews + reported misses that map to a prior `SUPPRESS`. Do not inflate Suppression Accuracy by counting unaudited suppressions as correct.

These metrics complement — they do not replace — the seven evaluation goals in [shadow-evaluation.md](./shadow-evaluation.md) (act-on hit, overestimate, timing, etc.).

## Counterfactual comparison (ultimate measure)

Later harness ([SE10](../../tickets/shadow/SE10-counterfactual-ab-harness.md)):

| System | Policy |
| --- | --- |
| **A** | Surface everything plausibly actionable |
| **B** | Enigma attention / suppress policy |

Compare over the same real window:

- useful items caught
- false interruptions
- important misses

The product question is the **tradeoff**, not a single accuracy number. Counterfactual is the long-horizon measure; stratified audits and miss reports are the near-term instruments.

## Shadow accuracy private UX (sketch)

Private (Shadow/Private) surface — **not** Demo Mode chrome. Ticket [SE09](../../tickets/shadow/SE09-shadow-accuracy-screen.md).

First-pass information architecture:

| Block | Content |
| --- | --- |
| Today | Suppressions logged, audits completed, misses reported |
| Audits queue | Stratified samples awaiting Should have surfaced / Fine / Unsure |
| Misses | Reported miss intake + failure-stage tags |
| Behavioural mismatches | Click-through adjudication (signal → verdict) |
| Metrics | Suppression Accuracy, Silent Miss Rate (and links into weekly SE03 review) |

No requirement to ship polished UI in the scaffold tickets — schema + route stubs + copy contracts are enough until S02–S04 storage/log land.

## How the channels combine

```text
                    ┌─────────────────────────────┐
  Candidate decide  │ Frozen snapshot (SE04)      │
  SURFACE|SUPPRESS  └──────────────┬──────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  Behavioural traces         Stratified audits          Reported misses
  (SE05 signals)             (SE06 labels)              (SE07 gold)
         │                         │                         │
         └─────────────┬───────────┴─────────────┬───────────┘
                       ▼                         ▼
              Adjudication / day freeze    Headline metrics (SE08)
                       │                         │
                       └──────────┬──────────────┘
                                  ▼
                     Counterfactual A/B (SE10) + S06 exit honesty
```

## Coordination with existing Shadow tickets

| Concern | Owner |
| --- | --- |
| Env / banner / refuse Demo migration | S01 (`done`) — do not re-edit |
| Shadow storage root | S02 |
| Notification delivery off | S03 |
| Attention log persistence | S04 (surface candidates; SE04 extends suppress snapshots) |
| Seven-goal comparison stubs | S05 |
| Exit / promote-from-Shadow | S06 (consume silence metrics) |
| Action ↔ attention join | SE01 |
| Would-notify suppress audit | SE02 (delivery-oriented; SE04 is decision-oriented) |
| Weekly review artefact | SE03 (rollup silence metrics + day freezes) |
| Silence prediction log, audits, misses, metrics, UX, A/B | **SE04–SE10** |
| Open-loop due phrase resolution (commitment bridge) | **SE11** · [open-loop-commitments.md](./open-loop-commitments.md) |

Prefer **soft (~)** dependencies on S01–S06 / SE01–SE03. Silence tickets must not edit `EnvironmentMode`, Demo attention UI, or start Gmail OAuth.

## Privacy

- Decision logs, audits, and miss reports stay on Shadow (or Private) roots — never Demo ([ADR-008](../adr/008-shadow-storage-roots.md)).
- Prefer PERSON_* / transformed subject refs in exportable artefacts; no wholesale Notes or raw attendee emails.
- Behavioural detectors must not ship keyloggers or clipboard monitors — only first-party Enigma-observed actions and source deltas already in Core.
- Remote models must not receive frozen snapshots wholesale without a dedicated ADR.

## Non-goals (this design track)

- Full Shadow product UI / onboarding funnel
- Changing Demo Mode attention freeze or `apps/web` demo attention files
- Implementing Gmail OAuth
- Claiming statistical significance without an agreed sample window
- Treating behavioural mismatch as automatic ground-truth failure
