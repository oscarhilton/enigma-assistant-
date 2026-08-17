# SEC-00 — Personal-data threat model

**Status:** done  
**Branch:** `ticket/SEC00-personal-data-threat-model`  
**Domain:** security (documentation)  
**May edit:** `docs/architecture/personal-data-security.md`, `docs/adr/021-personal-data-security-boundary.md`, `docs/adr/022-private-vault-storage.md`, `tickets/security/**`, `docs/architecture/overview.md`, `tickets/README.md`

**Hard depends:** [C09](../conversational-ui/C09-llm-conversational-boundary.md) (LLM/tool boundary landed)  
**Soft (~):** [ADR-012](../../docs/adr/012-reasoning-value-gate-decision.md) boundary-violation findings

## Goal

Document a **personal-data threat model** that treats email as hostile input, makes the LLM/Enigma Core split security-relevant, and covers the **full data lifecycle** — not only the network / LLM boundary ([ADR-021](../../docs/adr/021-personal-data-security-boundary.md), [ADR-022](../../docs/adr/022-private-vault-storage.md)).

Design goal: **compromise of any one ordinary boundary does not reveal the whole private world** — with honest limits for active malware while unlocked.

## Deliverables

### Network / LLM plane

- [x] Expand [personal-data-security.md](../../docs/architecture/personal-data-security.md) with full STRIDE-style or equivalent analysis for Gmail pilot
- [x] Explicit **indirect prompt injection** section (OWASP LLM Top 10) with attacker stories
- [x] Trust-boundary diagram aligned with [ADR-021](../../docs/adr/021-personal-data-security-boundary.md)
- [x] Attacker personas: malicious sender, compromised provider, misconfigured developer, curious LLM
- [x] Mitigation mapping → SEC-01 … SEC-06 tickets (SEC-05 gate verifies)

### Storage / lifecycle plane

- [x] **Asset inventory** with classification ([ADR-022](../../docs/adr/022-private-vault-storage.md)):
  - SECRET: OAuth refresh, MK, device keys, API keys
  - PRIVATE_RAW: email bodies, attachments, note bodies
  - PRIVATE_DERIVED: obligations, people graph, embeddings, FTS, vector index, summaries
  - REMOTE_SAFE: transformed egress payloads
  - PUBLIC: non-secret config
- [x] **Threat tier table** — what each layer defends and honest limits ([ADR-022](../../docs/adr/022-private-vault-storage.md#threat-tiers-explicit-limits))
- [x] Scenario write-ups with mitigations:
  - **Stolen laptop** (locked vs unlocked)
  - **Enigma dir copied** (`~/.enigma/private/` exfil without Keychain)
  - **Backup leaked** (Time Machine, manual export)
  - **Crash dumps / core dumps** containing decrypted pages
  - **Process compromise** while session unlocked (malware as user — honest "much harder, not impossible")
  - **Embedding / index side-channel** (plaintext vector DB beside encrypted vault)
  - **OAuth token stolen** (Keychain tier — ongoing access vs historical vault)
  - **Malicious attachment** (attacker-controlled parse input)
  - **Incomplete source deletion** (blob retained after user expects wipe)
  - **Unsafe logging** (bodies, tokens, prompts in production logs)

### Cross-cutting

- [x] Non-goals for v0-real (send/modify, autonomous reply, "impossible under malware" claims)
- [x] "Email is evidence, not instructions" stated as invariant

## Acceptance criteria

- [x] Every mitigation in SEC-01–SEC-06 traceable to at least one documented threat
- [x] Storage lifecycle threats co-equal with network/LLM threats in architecture doc
- [x] Threat tier table includes explicit honest limit column for each scenario
- [x] "Email is evidence, not instructions" stated as invariant
- [x] No contradiction with [ADR-004](../../docs/adr/004-notes-best-effort-no-sqlite.md), [ADR-005](../../docs/adr/005-demo-private-storage-roots.md), [ADR-020](../../docs/adr/020-llm-conversational-boundary-not-truth.md), [ADR-022](../../docs/adr/022-private-vault-storage.md), [privacy-model.md](../../docs/architecture/privacy-model.md)
- [x] M11 Gmail scaffold explicitly distinguished from pilot-ready connector (SEC-04)
- [x] Each SEC-05 lifecycle gate question maps to at least one threat scenario

## Test plan

Documentation review only — no runtime tests.

## Privacy constraints

Documentation only. Must state Demo/Private/Shadow separation ([ADR-005](../../docs/adr/005-demo-private-storage-roots.md), [ADR-008](../../docs/adr/008-shadow-storage-roots.md)) and that threat model covers **inbound** hostile content and **at-rest** theft vectors, not only outbound leakage.

**Unlocks:** SEC-01, SEC-02, SEC-03, SEC-04, SEC-06, SEC-05

## Related ADR

[ADR-021 — Personal data security boundary](../../docs/adr/021-personal-data-security-boundary.md) · [ADR-022 — Private vault storage](../../docs/adr/022-private-vault-storage.md) · [data-retention.md](../../docs/architecture/data-retention.md)

## Implementation notes

- Full threat model: [personal-data-security.md § Threat model](../../docs/architecture/personal-data-security.md#threat-model)
- 35 threat IDs (T-NET-01…18, T-STO-01…17); SEC-03 seed cases carry `threat_ids` in [`adversarial_email_cases.py`](../../packages/fixtures/src/personal_enigma/fixtures/adversarial_email_cases.py)
