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
for CI. Canonical life corpus is `scenarios/alex-v1/` (D08).

## Loader + seeded RNG

```python
from personal_enigma.simulation.scenario import load_scenario, scenario_rng

pkg = load_scenario("scenarios/alex-v1")
rng = pkg.rng()  # or scenario_rng("alex-v1")
```

Do not call unseeded randomness from scenario / corpus generation.
