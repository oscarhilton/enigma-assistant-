# Release conductor contract

One **release conductor** agent coordinates merge/release topology. It is not a swarm of parallel implementers.

## Mandate

The conductor MUST:

1. **Observe** current git state: branch name, dirty/clean worktree, recent commits, relationship to `main` and any stacked base branch.
2. **Read** the claimed ticket(s) under `tickets/` (status, package boundary globs, acceptance criteria, test plan).
3. **Map** open PRs (base/head, stack order, CI status when available via `gh` read-only).
4. **May request** bounded specialist audits (security, privacy, test gap) — but MUST reconcile every claim against repo evidence (files, diffs, test output).
5. **Choose** a single recommended action (see kinds below).
6. **Run** canonical verify commands appropriate to scope (see [cloud-agents.md](../cloud-agents.md)).
7. **Emit** one machine-shaped JSON handoff document conforming to [handoff-schema.json](./handoff-schema.json).

### `recommended_action.kind`

| Kind | When to use |
| --- | --- |
| `commit_on_branch` | More commits needed on the working branch before a PR exists |
| `open_pr` | No PR exists yet for this branch; propose opening one |
| `request_review` | A draft or open PR **already exists** — ask Oscar/reviewers to review (do **not** emit `open_pr` for an already-open PR) |
| `no_action` | Topology and verify are fine; nothing further for this conductor turn |
| `rebase_stack` | Stacked PR base/head must change (e.g. retarget after a lower PR merges) |
| `run_more_tests` | Evidence insufficient; name the missing verify commands |
| `stop_needs_human` | Ambiguous stack, secrets risk, or work outside read-only mandate |

The conductor MUST NOT (unless the job brief **explicitly authorizes**):

- `git push` (any remote)
- Open, update, or merge PRs
- Change ticket `Status` fields
- Alter production or shared storage configuration

Oscar-only merge is unchanged: the relay cannot merge; agents do not merge `main`.

## Economics (serial by default)

**Governing principle:** parallelise only when independence is real **and** saved wall-clock time is worth extra agent spend.

| Rule | Policy |
| --- | --- |
| Default shape | **Serial** — one implementation agent at a time |
| Target concurrency | **1** cloud agent |
| Normal max | **2** (second slot only for a genuinely independent ticket) |
| Slot 3 | **Reserved** for time-sensitive / independent work — not a standing parallel lane |
| Fixes | **Reuse** the implementation agent; do not spawn a reviewer/fixer swarm |
| Review | Do **not** `request_review` on a knowingly unstable head |
| Verify | Prefer **local / GitHub CI** for routine work; reserve cloud review agents for architecture, security, and high-risk boundaries |
| Model | Routine jobs use Cursor **true DEFAULT** by **omitting** `model` (see [relay.md](./relay.md)). Do not send `composer-2` “just in case.” |
| Merge | Oscar-only; unchanged |

This is orchestration policy, not a second constitution. It does not rewrite PolarIS, Council, or Observatory doctrine.

## Output handoff

Write JSON (stdout or agreed artifact path) with:

| Field | Purpose |
| --- | --- |
| `observed_state` | Branch, cleanliness, ticket ids, PR numbers |
| `evidence` | Commands run, file paths inspected, diff summaries |
| `scope_classification` | in_ticket \| scope_creep \| cross_ticket \| infra_only |
| `recommended_action` | Structured next step (see schema + kinds table) |
| `tests` | Commands run + pass/fail |
| `residual_risks` | Privacy, stack conflicts, missing CI |
| `requires_oscar` | Boolean + human-readable blockers |

## Verify commands (default cloud lane)

```bash
uv run pytest
uv run ruff check .
pnpm --dir apps/web test
```

Scope pytest to ticket paths when the job is ticket-bound.

## Escalation

Set `requires_oscar: true` when:

- Package boundary violations are present in the diff
- Stacked PR base branch is ambiguous
- Real secrets or storage roots appear in env or diffs
- Verify commands fail and fix is outside conductor read-only mandate
