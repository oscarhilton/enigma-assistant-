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
| Chat messages | **Very High** |
| Health / Photos | Out of MVP; Very High |

Notes frequently contain free-form private material. A note must **not** automatically ship wholesale through transformation into a hosted LLM.

Chat is the same family, with three named invariants ([C05e](../../tickets/conversational-ui/C05e-recent-source-queries.md)): **CHAT ≠ WORLD** (raw thread is evidence, never the world model); **QUOTE ≠ REMOTE CONTEXT** (verbatim bodies may render locally and must not enter Fireworks / `recent_dialogue` egress); **EXPIRY ≠ LOSS OF ALL UTILITY** (SEC-06 raw TTL can drop the quote while independently justified derived facts remain).

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

**Durable vault storage** adopts **purpose-scoped aliases** (project / social / egress scopes) so graphs do not auto-link across contexts — the resolver holds equivalence separately ([ADR-023](../adr/023-persistent-shadow-abstract-state-not-biography.md), [packages/identity](../../packages/identity)). Remote egress may use ephemeral per-request pseudonyms; stable global handles are a linkability risk in persistent shadow.

## Local embeddings

Raw Notes (and other private corpora) embeddings are generated **locally**. Do not send the complete Notes corpus to a hosted embeddings API. The remote reasoning model receives only retrieved, transformed passages.

Scaffold defaults: [`packages/privacy`](../../packages/privacy).

## Context compilation (request-shaped remote memory)

Select-first is not a redaction pass. Each remote turn **interprets a request profile**, then fetches only justified modules, transforms them for that purpose, and compiles a minimal model context ([ADR-029](../adr/029-context-compilation-request-shaped-memory.md)).

```text
USER REQUEST → INTERPRET PROFILE → CONTEXT REQUIREMENTS
  → FETCH permitted/relevant state → TRANSFORM → COMPILE → LLM
```

Every included module records a request-derived justification on `CompiledTurnManifest` (`EgressDisclosure.context_manifest`). No justification → the compiler does not fetch it. Context that is not required for this request does not enter the prompt.

The manifest is the privacy audit of the turn — not a second prompt. Cortex membrane events may show the request profile; FORENSIC disclosure shows include/exclude + justification.

Related: [conversational-stream.md](./conversational-stream.md) · [data-retention.md](./data-retention.md) · [SEC-07](../../tickets/security/SEC-07-shadow-reconstruction-benchmark.md).
