# Demo representation layers

Demo Mode surfaces the same underlying private world through three deliberate
layers. Do not collapse them in the UI.

## PRIVATE UI

What the fictional user would see locally:

- Maya, Atlas
- £14,300
- Friday 15:00

The **Attention** dashboard uses this layer.

## MODEL VIEW

What a hosted model may receive after privacy transforms:

- PERSON_A, PROJECT_B
- SIGNIFICANT_GBP_AMOUNT
- DATE_T_PLUS_2

**Why** and **Privacy inspector** views may show this layer so visitors can
contrast local knowledge with remote exposure.

## EXTERNAL ATTENTION

Coarsened outward summaries:

- A work follow-up
- An outstanding project commitment

Not the default dashboard copy.

## Related UX rules

- Priority (1–5) = how much this matters; Confidence (0–1) = how sure Enigma is.
- Attention rank is not raw confidence — a high-confidence low-importance signal
  must not outrank a medium-confidence high-urgency commitment.
- Reason codes are a machine layer under Why, not card body copy.
