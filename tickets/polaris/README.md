# Polaris search programme

Receding-horizon “life chess engine” for WORTH DOING. Docs constitution: [polaris-search.md](../../docs/architecture/polaris-search.md) · [council.md](../../docs/architecture/council.md) · [ADR-044](../../docs/adr/044-receding-horizon-action-search.md)–[048](../../docs/adr/048-structured-search-trace-and-lens.md).

**Status:** design captured. Claim **one ticket per agent**. Do not claim `future` tickets until hard deps are `done`.

## Principle

> Enigma does not optimise a person's life. It helps the user choose among locally available actions according to their own goals, constraints and current circumstances.

Search depth is an internal budget. Only ply-0 may be authorised. The Council is an advisory **projection** over one Enigma state — specialist lenses, not extra agents. Lens shows structured traces and Council assessments, not chain-of-thought.

## Tickets

| Ticket | Title | Status | Hard depends |
| --- | --- | --- | --- |
| [NORTHSTAR-SEARCH-DOCS](../northstar/NORTHSTAR-SEARCH-DOCS.md) | Reconcile North Star + ADRs | `in_progress` | — |
| [POLARIS-SEARCH-01](./POLARIS-SEARCH-01-decision-position.md) | `DecisionPosition` | `future` | NORTHSTAR-SEARCH-DOCS |
| [POLARIS-SEARCH-02](./POLARIS-SEARCH-02-move-generation-legality.md) | Move generation + legality | `future` | 01 |
| [POLARIS-SEARCH-03](./POLARIS-SEARCH-03-local-evaluator.md) | Local evaluator | `future` | 01 |
| [POLARIS-SEARCH-04](./POLARIS-SEARCH-04-receding-horizon-search.md) | Receding-horizon search | `future` | 02 + 03 |
| [POLARIS-SEARCH-05](./POLARIS-SEARCH-05-executive-motifs.md) | Motifs + strategy scripts | `future` | 04 |
| [ALEX-EVAL-01](../demo-evaluation/ALEX-EVAL-01-life-positions.md) | Replayable life positions | `future` | 01 (~ 04) |
| [ALEX-EVAL-02](../demo-evaluation/ALEX-EVAL-02-planner-tournament.md) | Planner tournament | `future` | ALEX-EVAL-01 + 04 |
| [BRAIN-01](../conversational-ui/BRAIN-01-structured-search-trace.md) | Structured search trace | `future` | 04 |
| [BRAIN-02](../conversational-ui/BRAIN-02-pv-explorer.md) | Lens PV explorer | `future` | BRAIN-01 |
| [BRAIN-03](../conversational-ui/BRAIN-03-live-recalculation.md) | Live invalidation | `future` | BRAIN-02 |
| [POLARIS-SEARCH-06](./POLARIS-SEARCH-06-shadow-mode.md) | Shadow beside current planner | `future` | 04 + ALEX-EVAL-02 + BRAIN-01 |
| [POLARIS-SEARCH-07](./POLARIS-SEARCH-07-controlled-promotion.md) | Drive Next Action only after evidence | `future` | 06 |

```text
NORTHSTAR-SEARCH-DOCS
        │
        ▼
     01 DecisionPosition
        │
        ├──────────────► ALEX-EVAL-01 (soft on 04)
        ▼
  02 legality     03 local eval
        \            /
         ▼          ▼
           04 search
          /    |    \
        05   BRAIN-01  ALEX-EVAL-02
               │
            BRAIN-02 → BRAIN-03
               │
               ▼
              06 shadow  →  07 promote
```

## Naming

| Name | Means |
| --- | --- |
| Enigma | Hidden substrate / canonical world model — not a character |
| Vault | Protected retained memory (ADR-022 / ADR-036) |
| Council | Advisory projection of specialist assessments over one position |
| Polaris | Chair / navigator — receding-horizon search; never overrides the user |
| Goose | Familiar / courier — no authority; must name incomplete coverage |
| Foundry | Capabilities + legality/effects; later physical/UI externalisation — not a searcher |
| C12 Life Scripts | Product-acceptance episodes |
| Strategy scripts | Polaris opening-book priors |
| Cortex | What Enigma did (C10) |
| Lens | Structured PV explorer + Council assessments (`BRAIN-*` tickets) |

Functional Council seats (internal ids; star aliases are copy only — [council.md](../../docs/architecture/council.md)):

| Internal id | Function | v1 |
| --- | --- | --- |
| `navigation` | Chair aggregate | Polaris (not a peer voter) |
| `body` | Training / capability / session fit | Definite (Aldebaran) |
| `nourishment` | Fuel / meals / groceries | Likely (Spica) |
| `recovery` | Sleep / fatigue / pacing | Definite (Canopus) |
| `people` | Promises / coordination | Likely; **name TBD** |
| `craft` | Work units / switch cost / blockers | Likely; **name TBD** |
| `stewardship` | Bills / admin / household | Candidate — earn via scenarios |
| `herald` | Forcing-change / replan | Sirius-as-Herald — not a voting peer |
| `chronicle` | Long horizon | Optional projection (Vega) |

Do **not** rename `ContextGraph`, `DecisionPosition`, `CandidateMove`, `PrivateVault`, `RetentionDecision`, or `SemanticRecall` after stars.
