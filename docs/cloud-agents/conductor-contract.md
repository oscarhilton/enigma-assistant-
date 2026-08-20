# Release conductor contract

One **release conductor** agent coordinates merge/release topology. It is not a swarm of parallel implementers.

## Mandate

The conductor MUST:

1. **Observe** current git state: branch name, dirty/clean worktree, recent commits, relationship to `main` and any stacked base branch.
2. **Read** the claimed ticket(s) under `tickets/` (status, package boundary globs, acceptance criteria, test plan).
3. **Map** open PRs (base/head, stack order, CI status when available via `gh` read-only).
4. **May request** bounded specialist audits (security, privacy, test gap) — but MUST reconcile every claim against repo evidence (files, diffs, test output).
5. **Choose** a single recommended action: branch to use, commits to include, PR base/head proposal, or "stop — needs human."
6. **Run** canonical verify commands appropriate to scope (see [cloud-agents.md](../cloud-agents.md)).
7. **Emit** one machine-shaped JSON handoff document conforming to [handoff-schema.json](./handoff-schema.json).

The conductor MUST NOT (unless the job brief **explicitly authorizes**):

- `git push` (any remote)
- Open, update, or merge PRs
- Change ticket `Status` fields
- Alter production or shared storage configuration

## Output handoff

Write JSON (stdout or agreed artifact path) with:

| Field | Purpose |
| --- | --- |
| `observed_state` | Branch, cleanliness, ticket ids, PR numbers |
| `evidence` | Commands run, file paths inspected, diff summaries |
| `scope_classification` | in_ticket \| scope_creep \| cross_ticket \| infra_only |
| `recommended_action` | Structured next step (see schema) |
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
