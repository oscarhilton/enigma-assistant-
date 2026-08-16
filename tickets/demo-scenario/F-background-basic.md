# Feature scenario stub — background-basic

| Field | Value |
| --- | --- |
| Status | `todo` |
| Domain | `demo-scenario` |
| Related | D08c, D03 |

## Intent

Canonical message surrounded by ~50 irrelevant background messages. Enigma should still surface the canonical obligation.

## Package boundary

- `scenarios/feature/background-basic/**`
- Ground-truth `signal_class` for background items (`expected_attention: false`)

## Acceptance

- [ ] Scenario package validates
- [ ] Critical recall holds with background present
- [ ] Source payloads omit `signal_class`
