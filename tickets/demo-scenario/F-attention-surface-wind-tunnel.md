# F-* attention surface regressions (wind tunnel)

| Field | Value |
| --- | --- |
| Status | `done` (covered by M06a unit fixtures) |
| Domain | `demo-scenario` / `attention` |
| Related | M06a, D14, D08d |
| Branch | `ticket/attention-surface-policy` |

## Intent

Capture the D14 alex-v1 “successful failure” dump as named regression fixtures.

## Fixtures

| ID | Covered in |
| --- | --- |
| `F-calendar-existence-is-not-attention` | `packages/attention/tests/test_surface_policy.py` + obligations merge |
| `F-past-calendar-event-resolves` | same |
| `F-automated-mail-is-not-commitment` | same |
| `F-newsletter-is-not-commitment` | same |
| `F-package-notification-is-not-commitment` | same |
| `F-social-question-is-pending-reply` | same |
| `F-unrelated-machine-mail-not-merged` | `packages/obligations/tests/test_surface_fixtures.py` |
| `F-distinct-social-plans-not-merged` | same |
| `F-low-priority-candidate-not-surfaced` | attention surface policy tests |

## Acceptance

- [x] Unit fixtures green without full scenario packages (tiny scenarios preferred)
- [x] Documented in [attention-surface.md](../../docs/architecture/attention-surface.md)
