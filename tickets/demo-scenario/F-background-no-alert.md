# Feature scenario — background-no-alert

| Field | Value |
| --- | --- |
| Status | `done` |
| Domain | `demo-scenario` |
| Related | D08d, D07 |
| Path | `scenarios/feature/background-no-alert/` |

## Intent

A simulated day with substantial email traffic but nothing requiring attention — zero attention items is correct.

## Acceptance

- [x] Eval expects empty attention surface
- [x] Suppression metrics still recorded (false-alert rate = 0 under silence)
