# Scenario packages

On-disk format for Demo Mode fictional lives. Owned by **D03** (schema +
validator); corpora are filled by later tickets (D08 Alex, D09 attacks, D12
product demo).

## Layout

```text
scenarios/<id>/
  scenario.yaml       Required manifest (+ optional inline events)
  persona.yaml        Optional fictional persona (not Enigma evidence)
  entities/           Optional YAML maps (contacts, orgs, places)
  timeline/           Optional *.yaml event lists
  content/            Optional email/note/attachment bodies
  ground_truth/       Optional eval truth (D06)
  attacks/            Optional adversarial packs (D09)
  recordings/         Optional provider replays (D11)
```

## Manifest (`scenario.yaml`)

| Field | Required | Notes |
| --- | --- | --- |
| `id` | yes | **Must** match the directory name |
| `version` | yes | Bump on released semantic change |
| `status` | no | `scaffold` \| `feature` \| `benchmark` \| `product-demo` |
| `timezone` | no | Default `UTC` |
| `start_at` | no | Required when any event uses relative `+2d` / `+3h` / `+30m` offsets |
| `seed` | no | Deterministic RNG seed (defaults to `id`) |
| `persona` | no | Path to persona file |
| `description` | no | Human summary |
| `events` | no | Inline event list (tiny feature packs) |

## Events (source layer only)

Events describe **evidence** adapters emit — never pre-baked obligations,
commitments, or attention items.

| Field | Notes |
| --- | --- |
| `id` | Unique within the package |
| `at` | ISO-8601 instant, or relative `+2d` / `+3h` / `+30m` from `start_at` |
| `type` | `email.receive`, `email.send`, `calendar.upsert`, `calendar.cancel`, `reminder.upsert`, `reminder.complete`, `note.upsert`, `contact.upsert` |
| `source` | `mail` \| `calendar` \| `reminders` \| `notes` \| `contacts` |
| `payload` | Source-shaped fields (subject, body, attendees, …) |
| `content_ref` | Optional path under `content/` |

Forbidden payload keys: `obligation(s)`, `commitment(s)`, `attention_item(s)`.

## Feature packs

Tiny packs under `scenarios/feature/` (≈5–10 events) exercise single behaviours
for CI. Canonical life corpus is `scenarios/alex-v1/` (D08). 0.2.1 is three January weeks. Six months of ordinary events is a **version bump** of the same package ([D08f](../tickets/demo-scenario/D08f-alex-six-month.md)) — nested `timeline/YYYY-MM/` dirs; not a second `alex-v2` fork. Do not create `ALEX_BIOGRAPHY.md`.

## Adversarial packs (D09)

Executable attack corpora live under `scenarios/feature/adversarial/`:

| Pack | Focus |
| --- | --- |
| `prompt-injection` | Jailbreak / override language in mail & notes |
| `secrets` | Synthetic API keys & passwords in private content |
| `re-identification` | Distinctive PII that must become `PERSON_*` only |
| `malicious-provider` | PAYG stub that hunts bait tokens |
| `provider-failure` | Transport errors must not fall back to private data |

Alex cross-links (forbidden-token lists) are under `scenarios/alex-v1/attacks/`.
Eval harness: `personal_enigma.evaluation.adversarial.run_adversarial_pack`.

## Loader + seeded RNG

```python
from personal_enigma.simulation.scenario import load_scenario, scenario_rng

pkg = load_scenario("scenarios/alex-v1")
rng = pkg.rng()  # or scenario_rng("alex-v1")
```

Do not call unseeded randomness from scenario / corpus generation.
