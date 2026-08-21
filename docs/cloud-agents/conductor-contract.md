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

## Model budgeting (relay dispatch)

- **Default / green:** Omit `model` on `dispatch` and `request_review` so Cursor applies its default/green model selection. The relay must not silently inject `composer-2` or `composer-2.5`.
- **Operating mix (observed 2026-08-21):** default/green was 16.1% vs target ≥60%; composer-2.5-fast alone was 46.4%. Steady-state target: default/green ≥60%, explicit premium <30%.
- **Explicit escalation:** Pass `model: "composer-2.5"` (or other allowlisted premium id) only after a substantive default-model attempt stalls, or for clearly high-complexity architecture work. Premium models (`composer-2.5*`, grok, `gpt-5*`, thinking) require `model_escalation_reason` (8–240 chars); the relay rejects premium requests without it.
- **Never premium for:** status polling, reporting, ordinary CI bookkeeping, straightforward review fixes, routine test reruns.
- **Testing while iterating:** ticket-scoped pytest/commands; canonical suites (`uv run pytest`, `pnpm test`, etc.) at pre-push/PR gates and after final review-fix batches unless the ticket requires otherwise.
- **Escalation cap:** after one substantive premium escalation without reducing uncertainty, stop/reassess — do not repeatedly escalate.
- **Allowlist:** When `model` is provided, it must still pass the relay model allowlist (`RELAY_ALLOWED_MODELS`).

## Escalation

Set `requires_oscar: true` when:

- Package boundary violations are present in the diff
- Stacked PR base branch is ambiguous
- Real secrets or storage roots appear in env or diffs
- Verify commands fail and fix is outside conductor read-only mandate
