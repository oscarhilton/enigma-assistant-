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

## Alex fixture sensitivity

The canonical **Alex Morgan** demo corpus lives under `scenarios/alex-v1/` (see
also `packages/fixtures/.../demo_checkpoints.py`). It is **fictional** and
benchmark-grade — not real personal data. Six months of **ordinary events**
(not a biography) is a version bump of that same package
([D08f](../../tickets/demo-scenario/D08f-alex-six-month.md)); do not duplicate
Alex under `packages/fixtures/alex/`.

**Fixtures are the source of truth.** Authored messages, events, emails, and
relationships **are** Alex. Do **not** add an omniscient biography
(`ALEX_BIOGRAPHY.md` or equivalent). `persona.yaml` is author scaffolding, not a
life to reconstruct. [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md)
evaluators attack the stripped shadow as **outsiders** — they must not be handed
a compiled mystery.

| Tier | What appears in Alex v0.2.1 | Examples |
| --- | --- | --- |
| **LOW** | Work logistics, fictional `@example` / `@northwind.example` contacts, calendar titles, promo noise | Q1 roadmap, design tokens, team standup, newsletters |
| **MODERATE** | Personal/social context without precise identifiers | Partner dinner, brunch with parents, climbing with friend, city-level “London” |
| **HIGH** | — | **Not present** in the released Alex timeline |

The released Alex corpus does **not** include credentials, bank account numbers,
exact street addresses, medical diagnoses, exact salary amounts, or API secrets.
Adversarial **injection** cases are named in `adversarial_email_cases.py`; a
separate **D9 secrets** feature pack (`scenarios/feature/adversarial/secrets`)
holds synthetic credential-shaped strings for egress regression.

### Synthetic sensitive canary pack (SEC testing — opt-in overlay)

**FICTIONAL / SYNTHETIC ONLY** — for security crash-testing, **not** demo narrative
or Alex behavioural truth:

```
Alex v0.2.1
├─ authored behavioural timeline (scenarios/alex-v1/) — unchanged
├─ background/noise corpus (noise.yaml, background.yaml)
└─ security overlay (OPT-IN ONLY)
   └─ alex_sensitive_canaries.py
```

| Module | Purpose |
| --- | --- |
| `alex_sensitive_canaries.py` | Canary records with `SensitiveCanary` metadata (`raw_marker`, `allowed_shadow_features`, `forbidden_remote_semantics`) |
| `alex_security_canaries.py` | SEC manifest + grep targets (source → egress → shadow → stolen-dir) |
| `alex_security_overlay.py` | Opt-in loader — `ENIGMA_SECURITY_PROFILE=1` or `load_security_overlay=True` |
| `data/security_canaries/*.md` | Optional email/note bodies |

Used by SEC-02 (egress wire must not contain sentinels) and SEC-07 (shadow
reconstruction must not recover sentinels — exact grep **and** semantic scorer stub).
**Never** merge canaries into the immutable `alex-v1` benchmark timeline without a
version bump. Normal attention/evaluation runs exclude canaries by default.

### SEC-04 nasty test mailbox manifest (Google TEST account only)

**FICTIONAL / SYNTHETIC ONLY** — hostile mailbox matrix for proving the real Gmail
ingestion path does not bypass the private architecture. **Not** Oscar's inbox.

| Module | Purpose |
| --- | --- |
| `nasty_mailbox_manifest.py` | Matrix categories → fixture refs (adversarial cases, canaries, Gmail JSON) |
| `adversarial_email_cases.py` | SEC-03 injection corpus (re-run through real ingestion in SEC-04) |
| `alex_sensitive_canaries.py` | Canary secrets row in matrix |
| `packages/ingestion/tests/fixtures/gmail/nasty/` | Gmail API JSON stubs for MIME-specific rows |

Matrix categories: plain-text injection, HTML-hidden injection, quoted/reply content,
multipart MIME, malicious attachment metadata, fake system instructions, embedded
URLs/tracking, oversized/malformed bodies, canary secrets from `alex_sensitive_canaries`.
