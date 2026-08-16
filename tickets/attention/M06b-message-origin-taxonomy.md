# Follow-up — MESSAGE_ORIGIN taxonomy

| Field | Value |
| --- | --- |
| Status | `todo` |
| Domain | `attention` |
| Related | M06a (pragmatic first cut landed) |

## Intent

Replace heuristic brand / subject noise lists with a proper `MESSAGE_ORIGIN` (or equivalent) taxonomy: human thread, newsletter, marketing, automated notification, package, calendar confirmation, spam-like, etc.

## Non-goals

- Do not block M06a surface policy
- Do not invent D08f

## Acceptance (when claimed)

- [ ] Origin enum on ingestion / attention boundary
- [ ] Noise layer + attention classify consume the same taxonomy
- [ ] F-* noise fixtures still green
