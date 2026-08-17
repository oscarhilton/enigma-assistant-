# Alex v1 — support contract truth checklist

Evaluator-only ground truth for Reasoning Value Gate (R-L01). One row per arc in `scenarios/alex-v1/ground_truth/support_contracts.yaml`.

| Scenario | Behaviour | Valid from | Valid until | Resolution event | Expected surface window | Obligation | Good next actions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| checkout-q1-decision | MUST_SURFACE | 2026-01-13T08:00Z | 2026-01-14T17:00Z | w2-rem-checkout-done | Mon 13 Jan through Tue 14 Jan — two-option recommendation frame | obligation_checkout_rec | make_recommendation, compare_q1_vs_park, draft_two_options |
| checkpoint-2026-01-21T13:30 | MUST_SURFACE | 2026-01-21T13:00Z | 2026-01-21T14:00Z | w3-rem-tokens-done | Wed 21 Jan 13:00–14:00 UTC — attention (brunch) ≠ next action (token prep) | obligation_brunch_book | book_brunch_restaurant, prepare_token_review |
| climbing-dinner-social | MAY_SURFACE | 2026-01-15T08:00Z | 2026-01-17T18:00Z | — | Wed 15 Jan through Fri 17 Jan — warm reply without fake urgency | obligation_tom_climb | confirm_climbing_time, reply_to_tom |
| december-expenses | MUST_SURFACE | 2026-01-14T09:00Z | 2026-01-16T10:00Z | w2-rem-expenses-done | Tue 14 Jan through Fri 16 Jan morning — 5 min receipt gather, not DO EXPENSES | obligation_december_expenses | gather_receipts, open_expenses_form, submit_if_ready |
| dentist-critique-overlap | CONTEXT_ONLY | 2026-01-15T08:00Z | 2026-01-16T08:00Z | w2-cal-dentist-cancel | Wed 15 Jan conflict window; after Thu 16 Jan 08:00 cancel — CONTEXT_ONLY, do not re-nag | — | resolve_calendar_conflict, cancel_dentist_appointment |
| elena-dinner-wine | MUST_SURFACE | 2026-01-08T12:00Z | 2026-01-08T17:00Z | w1-rem-wine-done | Thu 8 Jan afternoon — buy wine before dinner, not morning-of | obligation_elena_dinner_wine | buy_wine_thursday_afternoon, confirm_dinner_time |
| elena-parents-brunch | MUST_SURFACE | 2026-01-20T08:00Z | 2026-01-22T12:00Z | w3-rem-brunch-done | Mon 20 Jan through Wed 22 Jan noon — book restaurant before Saturday parents visit | obligation_brunch_book | book_brunch_restaurant, check_availability_saturday, confirm_with_elena |
| machine-notifications | MUST_SUPPRESS | — | — | — | Always suppress — automated machine notifications | — | suppress_automated_notification |
| newsletters-promos | MUST_SUPPRESS | — | — | — | Always suppress — newsletters and SaaS promos | — | suppress_newsletter |
| prizzevault-junk | MUST_SUPPRESS | — | — | — | Always suppress — PrizeVault marketing junk | — | suppress_marketing |
| q1-priorities-friday | MUST_SURFACE | 2026-01-08T08:00Z | 2026-01-09T16:00Z | w1-rem-roadmap-done | Wed 8 Jan morning through Fri 9 Jan before Maya's 4pm deadline | obligation_q1_roadmap | pick_three_priorities, draft_q1_outline, send_to_maya |
| quiet-periods | MUST_STAY_QUIET | 2026-01-10T10:00Z | 2026-01-11T18:00Z | — | Sat 10 Jan morning through Sun 11 Jan evening — restful weekend, no manufactured urgency | — | suggest_walk, suggest_rest, suggest_micro_admin |
| sam-empty-state-reply | MAY_SURFACE | 2026-01-23T17:00Z | 2026-01-25T18:00Z | — | Fri 23 Jan evening through Sun 25 Jan — tiny reply, avoid stale re-alerts | obligation_empty_states | draft_short_reply, send_empty_state_decision, reply_to_sam |
| token-inventory-blocker | MUST_SURFACE | 2026-01-19T09:00Z | 2026-01-21T13:00Z | w3-rem-tokens-done | Mon 19 Jan through Wed 21 Jan 13:00 — surface Figma link as next action | obligation_token_audit | open_figma_link, finish_spacing_section, draft_token_inventory |
