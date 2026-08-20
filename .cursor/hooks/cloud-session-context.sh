#!/usr/bin/env bash
# Inject cloud-agent operating constraints and release-conductor context at session start.
set -euo pipefail

cat <<'CTX'
{
  "continue": true,
  "additional_context": "Cloud agent lane (personal-enigma): You are a worker OR a release conductor per the job brief. Workers: claim one ticket from tickets/, stay inside its package boundary globs, never access real home Enigma storage roots or HMAC secrets, use mocks only. Conductor: read docs/cloud-agents/conductor-contract.md — reconcile branch, dirty worktree, tickets, and open PR relationships against repo evidence; may request bounded specialist audits but must reconcile their output; run canonical verify commands; output JSON handoff per docs/cloud-agents/handoff-schema.json; NEVER push, open PR, or change ticket status unless the job explicitly authorizes. Verify before claiming done: uv run pytest (ticket-scoped or full), uv run ruff check ., pnpm --dir apps/web test; macOS-only: apps/apple-bridge local test lane. Implementation jobs: open PR when done; do not merge unless Oscar asks."
}
CTX
