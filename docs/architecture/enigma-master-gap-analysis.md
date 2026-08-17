# Enigma Master Gap Analysis

**Status:** Draft implementation brief  
**Source brief:** `THE Goose, Fully Squeezed` programme plan  
**Purpose:** map the current repo to the target architecture before adding more machinery

## Layer map

### Enigma Fundamentals

Already present and reusable:
- `apps/api/src/personal_enigma/api/context_compilation.py`: request-shaped compilation, explicit evidence domain, authority separation, capability families
- `apps/api/src/personal_enigma/api/conversation_context.py`: capsule, subject focus, unresolved request, turn-local constraints
- `apps/api/src/personal_enigma/api/respond_grounding.py`: fail-closed grounding fence
- `apps/api/src/personal_enigma/api/evidence_bundle.py`: mission, searched/empty/unsearched/unavailable sources, coverage adequacy
- `packages/domain/src/personal_enigma/domain/retention.py`: lineage, retention class, forget-compatible derivative metadata

Present but semantically weak:
- `EvidenceBundle.evidence` was ids-only and coverage-focused; proposition-shaped knowledge was implicit
- challenge semantics were mostly prose/fallback behavior rather than typed substrate
- continuity has capsule/focus, but no explicit handoff or turn contract object
- event/agent-work lifecycle is partly implied across traces and UI, not a typed semantic spine

Missing and needed now:
- canonical epistemic status enum that survives confidence
- canonical grounded assertion model
- first-class unknowns/challenges tied to a request

Missing but later:
- full handoff model
- shared-culture memory substrate
- typed agent-work/event spine
- durable life-memory graph over grounded assertions
- vector recall over assertion IDs

### Design North Star

Already present and reusable:
- `docs/architecture/overview.md`
- `docs/architecture/conversational-ui.md`
- `docs/architecture/conversational-stream.md`
- `docs/architecture/cortex-visualizer.md`
- multiple tickets enforcing “world state is truth”, “no fake thinking”, and “one speaking orchestrator”

Present but semantically weak:
- the repo has good local rules, but lacks a single programme-level map connecting knowing, challenging, remembering, understanding, attending, acting, disclosing, and forgetting

Missing and needed now:
- a repo-level mapping document tying the existing slices to the master plan vocabulary

### Product Language

Already present and reusable:
- `apps/web/src/enigma/courier.ts`
- `apps/web/src/enigma/EvidenceCourier.tsx`
- `docs/adr/034-evidence-coverage-bundle.md`

Present but semantically weak:
- current copy is specific to `Miso` but does not yet state the stricter “projection only” Goose boundary around scheduling, retries, escalation, and interruption

Missing and needed now:
- explicit product-language rule that core state drives Goose state and never the reverse

### Shared Culture

Already present and reusable:
- tone-memory doctrine already forbids psych dossier behavior
- capsule/context already distinguish discourse continuity from truth

Present but semantically weak:
- there is no explicit shared-convention substrate yet

Missing but later:
- minimal shared-convention memory distinct from facts, authority, and retention justification

## Terminology map

| Master-plan term | Current repo seam |
| --- | --- |
| EvidencePack | `EvidenceBundle` + compiled remote context |
| KNOW | compiler + tools + grounding fence + bundle |
| CHALLENGE | currently partial via coverage adequacy and grounding fallback |
| REMEMBER | retention lineage + world state + capsule separation |
| UNDERSTAND | capsule, recent dialogue projection, referent resolution |
| ATTEND | `packages/attention` projections |
| ACT | Assist funnel and authority ladder |
| DISCLOSE | egress gate + manifest |
| FORGET | SEC-06 retention lineage and forget routes |
| Goose seam | courier UI over bundle state |

## Minimum first delta

Do now:
1. Add canonical grounding models in `packages/domain`.
2. Extend `EvidenceBundle` with grounded assertions, unknowns, and typed challenges.
3. Keep those new structures ephemeral and request-shaped.
4. Tighten product-language docs so Goose/courier remains a pure projection.

Do not build yet:
- a new truth database
- a full life graph
- a serial multi-agent orchestration layer
- a shared-culture memory engine
- a Goose-driven scheduler

## Proof plan

The first slice is successful when the repo can represent:

- a verified observation without flattening it into “confidence”
- a missing fact as `unknown`, not invention
- a useful-but-insufficient signal as `qualifies`, not `confirms`
- a bundle that can answer “what did I establish?” separately from “did I search enough?”

That gives the later continuity, Brain, Cortex, and proactivity work a serious substrate to stand on.
