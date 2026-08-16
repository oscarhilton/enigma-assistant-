# Attention surface policy

**Status:** pragmatic first cut (post–D14 wind tunnel)  
**Related:** M06, D08d, D14 · F-* fixtures under `packages/attention/tests/test_surface_policy.py`

## Wind tunnel — successful failure

Running live Demo Attention on `alex-v1` produced a useful dump: the pipeline worked, but the **surface** was wrong. Calendar existence, machine mail, and open-thread spam dominated a view that should show ~2 high-priority items (brunch booking + token inventory).

That dump is the regression oracle for the F-* cases below.

## Hard rules

1. **Scheduled existence is not an obligation.** Calendar may *evidence* an obligation; it rarely *is* the obligation. Bare standup / 1:1 / dentist → context, not `AttentionItem`.
2. **Past calendar events resolve** — they must not linger as forever-OVERDUE with a “Deadline approaching” glance.
3. **Machine noise is never `INFERRED_COMMITMENT`** — newsletters, package notifications, PrizeVault / BuildCloud / RouteFox patterns.
4. **Default view ≠ all candidates.** Surface priority ≥ 4 (and ≥ 3 when timing warrants). Priority 2 stays dormant / open-loop.
5. **Do not mega-merge** unrelated social plans or machine mail via glue tokens (`with`, day names, brand spam).

## Kind bands (1–5)

| Kind | Priority | Default surface? |
| --- | --- | --- |
| `EXPLICIT_REMINDER` | 5 | yes |
| `INFERRED_OBLIGATION` | 4 | yes |
| `CALENDAR_OBLIGATION` | 3 | rare (exceptional only) |
| `INFERRED_COMMITMENT` | 2 | candidate only |
| `PENDING_REPLY` | 2 | candidate only (social questions) |

## Deadline why-now

Injected clock phases: `FUTURE` · `APPROACHING` · `DUE_SOON` · `DUE_TODAY` · `OVERDUE` · `STALE`.  
Never label a past due as “Deadline approaching”.

## F-* fixtures

| ID | Intent |
| --- | --- |
| `F-calendar-existence-is-not-attention` | Bare calendar quiet |
| `F-past-calendar-event-resolves` | Past events drop / STALE |
| `F-automated-mail-is-not-commitment` | BuildCloud / PrizeVault |
| `F-newsletter-is-not-commitment` | Design Weekly |
| `F-package-notification-is-not-commitment` | RouteFox |
| `F-social-question-is-pending-reply` | Quick sync? |
| `F-unrelated-machine-mail-not-merged` | No PrizeVault mega-item |
| `F-distinct-social-plans-not-merged` | Dinner ≠ Climbing |
| `F-low-priority-candidate-not-surfaced` | P2 not on default view |

## Follow-ups (ticketed, not in this cut)

- Full `MESSAGE_ORIGIN` taxonomy beyond heuristic noise brands
- Exceptional calendar surfacing (soon+prep, changed, conflict)
- Richer OPEN_REQUEST vs USER_COMMITMENT language models
