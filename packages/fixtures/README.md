# Synthetic fixture pipeline (M02)

Deterministic builders and scenario packs for Enigma tests. **Synthetic only** —
no real personal data, live APIs, or production seeding.

## Builders

| Function | Domain model |
| --- | --- |
| `build_calendar_event` | `PrivateCalendarEvent` |
| `build_reminder` | `PrivateReminder` |
| `build_contact` | `PrivatePerson` |
| `build_note` | `PrivateNote` |
| `build_message` | `PrivateMessage` |

Defaults use fixed IDs, `FIXTURE_EPOCH` timestamps, and `@example.test` addresses.
Pass keyword overrides for any field.

```python
from personal_enigma.fixtures import build_reminder

rem = build_reminder(title="Review proposal", due_at=...)
```

## Scenario packs

Cross-source bundles used by later milestones (especially M15):

| Name | Contents |
| --- | --- |
| `review_proposal` | Reminder + Gmail follow-up + calendar meeting → expected `Obligation` |

```python
from personal_enigma.fixtures import InMemoryFixtureStore, review_proposal_scenario

pack = review_proposal_scenario()
store = InMemoryFixtureStore()
store.load_scenario(pack)
assert pack.expected_obligation is not None
```

## Determinism

Re-calling builders / `review_proposal_scenario()` yields equal models (same IDs,
timestamps, and evidence). Safe for equality and snapshot tests.
