#!/usr/bin/env bash
# Block shell commands that would reach real Private/Demo storage or secrets.
# Cloud agents must use mocks and workspace-local temp dirs only (ADR-005, ADR-008).
set -euo pipefail

input="$(cat)"
command="$(echo "$input" | jq -r '.command // empty')"

deny() {
  local msg="$1"
  jq -n \
    --arg msg "$msg" \
    --arg agent "Cloud agent boundary hook blocked this command. Use mocks and workspace-local paths only." \
    '{permission: "deny", user_message: $msg, agent_message: $agent}'
  exit 2
}

if echo "$command" | grep -qE 'git push[^;|&]*\s+(origin\s+)?(main|master)\b'; then
  deny "Cloud agents must not push to origin main or master. Use a ticket branch and open a PR."
fi

if echo "$command" | grep -qE 'git push[^;|&]*(-f|--force|--force-with-lease)'; then
  deny "Force push is blocked in cloud agent sessions."
fi


_storage_pat='(~/.enigma|/Users/[^/]+/\.enigma|ENIGMA_(PRIVATE|DEMO|SHADOW)_STORAGE)'
if echo "$command" | grep -qE "$_storage_pat"; then
  deny "Cloud agents cannot access real Enigma storage roots."
fi

_secret_pat='(PRIVATE_HMAC_KEY|GOOGLE_CLIENT_SECRET|GMAIL_TOKEN|APPLE_BRIDGE_TOKEN)'
if echo "$command" | grep -qE "$_secret_pat"; then
  deny "Cloud agents must not load or echo real connector/HMAC secrets."
fi

if echo "$command" | grep -qE '(^|[;&|]\s*)swift test|apps/apple-bridge.*swift'; then
  deny "Swift/Apple Bridge tests run on the local macOS lane only. Use mocks in cloud CI."
fi

echo '{ "permission": "allow" }'
exit 0
