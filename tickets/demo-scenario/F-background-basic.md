# Feature scenario stub — background-basic

| Field | Value |
| --- | --- |
| Status | `done` |
| Domain | `demo-scenario` |
| Related | D08c, D03, D08e |

## Intent

Canonical message surrounded by ~50 irrelevant background messages. Enigma should still surface the canonical obligation.

## Package boundary

- `scenarios/feature/background-basic/**`
- Ground-truth `signal_class` for background items (`expected_attention: false`)

## Acceptance

- [x] Scenario package validates
- [x] Critical recall holds with background present (fixture + GT)
- [x] Source payloads omit `signal_class`
