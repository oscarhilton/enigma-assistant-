# Privacy model

Governing principle:

> **Select first; transform second; transmit last.**

Apple services enrich Enigma’s private model of the user’s world; they do not enlarge the remote model’s view of it.

## Default remote privacy levels

| Source | Default risk |
| --- | --- |
| Email | Medium |
| Calendar | Medium |
| Reminders | Medium |
| Contacts | High |
| Notes | **High** |
| Messages / Health / Photos | Out of MVP; Very High |

Notes frequently contain free-form private material. A note must **not** automatically ship wholesale through transformation into a hosted LLM.

```text
Note
  │
  ▼
local relevance detection
  │
  ├── irrelevant → ignore
  └── relevant
         ↓
   extract minimal passage
         ↓
      Enigma transform
         ↓
   leakage analysis
         ↓
   remote / local decision
```

## Contacts and pseudonyms

`PrivatePerson` never goes to the remote LLM. Entity resolver maps to stable opaque IDs (e.g. `PERSON_A4F91C`) via local identity anchors (Contacts + emails + aliases + HMAC).

## Local embeddings

Raw Notes (and other private corpora) embeddings are generated **locally**. Do not send the complete Notes corpus to a hosted embeddings API. The remote reasoning model receives only retrieved, transformed passages.

Scaffold defaults: [`packages/privacy`](../../packages/privacy).
