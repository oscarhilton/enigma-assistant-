# Shadow evaluation rubric

**Status:** Design + tickets (SE01–SE03) — no full UI; no `EnvironmentMode` / banner changes (S01 `done` #65)  
**Questions list:** [shadow-mode-questions.md](./shadow-mode-questions.md)  
**Mode scaffold:** [shadow-mode.md](./shadow-mode.md) · S01–S06 under `tickets/shadow/`  
**Tickets:** [SE01](../../tickets/shadow/SE01-action-vs-attention.md) · [SE02](../../tickets/shadow/SE02-suppressed-notification-audit.md) · [SE03](../../tickets/shadow/SE03-weekly-shadow-review.md)  
**Minimal stubs:** [shadow-eval-stubs/](./shadow-eval-stubs/) (`UserAction`, `ShadowAttentionCandidate`, `SuppressedNotificationAudit`, weekly review JSON + Markdown)

## Why Demo cannot answer these

Demo Mode (Alex + corpus) has **authored ground truth**. Shadow Mode has a **real life** and only **behavioural evidence**. The seven questions below are the evaluation goals for Phase 3 observation — not product features to ship in a dashboard.

```text
DEMO EVAL                         SHADOW EVAL
─────────                         ───────────
Scenario ground_truth/*.yaml      User actions + time
Synthetic obligations             Real inbox / calendar / reminders
Precision vs labels               Precision vs what the user did
Notifications N/A                 Would-notify log (suppressed)
```

**Hard separation:** Shadow evaluation artefacts never mix Demo scenario DBs, HMAC keys, or Alex labels into scores for a real person ([ADR-005](../adr/005-demo-private-storage-roots.md)). Soft-dep on S01 storage / mode work; this doc does **not** introduce `EnvironmentMode.SHADOW`.

## Rubric (seven questions → observables)

| # | Question | Primary observable | Artefact / ticket |
| --- | --- | --- | --- |
| 1 | **Act-on recognition** — Does Enigma recognise what I act on? | Join of `UserAction` ↔ prior `ShadowAttentionCandidate` (hit / miss / late) | SE01 |
| 2 | **Nearly forgot** — Catch near-misses, not only obvious items? | Actions taken close to deadline with little prior user engagement; scored if Shadow ranked them highly earlier | SE01 + SE03 |
| 3 | **Importance overestimate** — False urgency in a real inbox? | High-rank / would-notify items the user never touches in a defined window | SE01 + SE02 |
| 4 | **Inferred relationships correct?** | Sample of PERSON_* / recurring-attendee inferences vs user confirmation or correction events (stub protocol) | SE03 (weekly sample) |
| 5 | **Accumulated memory improve judgement?** | Week-over-week curves: act-on hit rate, overestimate rate, near-miss catch rate | SE03 |
| 6 | **Timing (“now is good”) vs reality?** | Δt between Shadow “surface now” timestamp and user action / deadline | SE01 |
| 7 | **Misses synthetic never taught?** | Qualitative + tagged miss taxonomy on real noise (threads, billing, travel, family, etc.) absent from Alex | SE03 miss log |

### Scoring vocabulary (stubs)

Keep metrics local, coarse, and exportable as JSON — not a hosted analytics product.

| Metric | Definition (v0) |
| --- | --- |
| `act_on_hit` | User acted on entity X within window W after Shadow ranked X in top-K (or would-notify) |
| `act_on_miss` | User acted on X; Shadow never ranked X above threshold before the action |
| `late_hit` | Hit, but first Shadow rank after a useful lead-time threshold |
| `overestimate` | Would-notify / top-K item with zero user engagement in window W |
| `near_miss_catch` | Near-deadline action where Shadow had ranked the obligation ≥ threshold ≥ lead hours earlier |
| `timing_error_hours` | Signed hours: `t_action_or_deadline - t_shadow_surface` |
| `novel_miss_tag` | Free-text / enum tag for failure modes Demo never exercised |

Thresholds and window lengths are **configuration**, not hard-coded product claims. First implementation should snapshot the config into every weekly review artefact.

## Instrumentation (no full UI)

### 1. User actions vs attention (SE01)

Append-only local events (Shadow storage root only):

```text
UserAction {
  id, observed_at,
  kind: open | reply | complete | reschedule | dismiss | other,
  subject_ref,          # obligation / message / event id (transformed refs preferred)
  source_hint           # mail | calendar | reminder | …
}

ShadowAttentionCandidate {
  id, generated_at,
  subject_ref, rank, score,
  would_notify: bool,   # true iff delivery policy would have alerted (still suppressed)
  reason_codes[]        # coarse; no raw Note bodies
}
```

Comparator (stub OK): emit `{hits, misses, late_hits, overestimates, timing_errors[]}` for a time range. **Do not** read Demo `ground_truth/*.yaml` as labels for a real user.

### 2. Suppressed notifications audit (SE02)

Every time Shadow attention would have notified under Private policy, write an audit row **instead of delivering**:

```text
SuppressedNotificationAudit {
  id, would_have_notified_at,
  candidate_id,
  channel: tray | os | in_app | other,
  suppression_reason: "shadow_mode",
  rank, score, subject_ref
}
```

Hostile test target (when code lands): exploding notifier must never be invoked; audit row count ≥ would-notify candidates.

Soft-depends on S02 (structural suppression). SE02 owns the **audit artefact and metrics**, not the delivery gateway itself if S02 already claims that boundary.

### 3. Weekly Shadow review artefact (SE03)

One file (or folder) per ISO week under the Shadow root, e.g. `~/.enigma/shadow/reviews/YYYY-Www.json` (+ optional human Markdown). Contents:

| Section | Purpose |
| --- | --- |
| Config snapshot | Windows, top-K, lead-time thresholds |
| Rubric scores | Metrics for questions 1–3, 5–6 |
| Relationship sample | Small set of inferred ties for human yes/no (q4) — local only |
| Novel misses | Tagged examples for q7 |
| Suppression summary | Counts from SE02 audit |
| Privacy note | No wholesale Notes; prefer PERSON_* / transformed refs |

**No full UI** in SE01–SE03: CLI or local file open is enough. Desktop tray copy may eventually link here (E04) but is out of scope.

## What “good enough to leave Shadow” looks like (exit sketch)

Not a hard gate yet — record intent so later ADRs can harden numbers:

- Act-on hit rate trending up (or stable-high) across ≥ N weeks
- Overestimate / would-notify waste rate below an agreed ceiling
- Near-miss catch rate non-zero on real deadlines the user nearly missed
- Timing errors not systematically “too late”
- At least one documented **novel miss** class fed back into Demo/corpus or attention policy (or explicitly deferred)
- Relationship sample error rate known (even if high — honesty > silence)

## Coordination with S01–S06 scaffold

| Concern | Owner |
| --- | --- |
| `EnvironmentMode.SHADOW`, banner, refuse Demo migration | **S01** (`done` #65) — do not re-edit from SE* |
| Shadow storage root / keys | S02 |
| Notification delivery short-circuit | S03 (soft for SE02) |
| Attention log persistence | S04 (soft for SE01) |
| Comparison stub interfaces (seven goals) | S05 (soft for SE01–SE03) |
| Exit / promote-from-Shadow gate | S06 (soft for SE03) |
| Rubric observables, action join, suppress audit, weekly review | **This track (SE01–SE03)** |

Prefer **soft (~)** dependencies. SE* must not edit `packages/simulation/.../environment.py`, Shadow banner UI, or ADR-008 storage policy.

## Privacy

- Evaluation artefacts stay on the Shadow (or Private) storage root — never Demo.
- Prefer PERSON_* and transformed subject refs; no raw attendee emails or Notes bodies in review exports meant for sharing.
- Never send wholesale action logs or mail bodies to a hosted model to “score” Shadow weeks without a dedicated ADR.
- Remote inference remains disable-able; Shadow observation must still function for local metrics.

## Non-goals

- Full Shadow / Private product UI or onboarding funnel
- Claiming statistical significance without an agreed sample window
- Migrating Alex Demo ground truth into Shadow scores
- Changing attention ranking algorithms in SE* tickets (measure first)
