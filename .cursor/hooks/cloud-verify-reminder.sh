#!/usr/bin/env bash
# Remind cloud agents to run canonical verification before claiming completion.
set -euo pipefail

cat <<'MSG'
{
  "followup_message": "Before marking this job done: run ticket-scoped or canonical tests (uv run pytest, uv run ruff check ., pnpm --dir apps/web test). Behavioural changes require tests. Conductor jobs must emit JSON handoff per docs/cloud-agents/handoff-schema.json. Do not push to main/master or force-push unless explicitly authorized."
}
MSG
