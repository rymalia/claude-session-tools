#!/bin/bash
# Emit everything /session-summary needs in a single invocation, so users
# only need one permission allowlist entry. Output is key: value lines;
# missing fields are omitted so the caller can treat absence as "not
# applicable." Fields: now, project, branch, open_prs.

set -u

echo "now: $(date '+%Y-%m-%d %I:%M %p %Z')"
echo "project: $(basename "$PWD")"

branch="$(git branch --show-current 2>/dev/null || true)"
if [ -n "$branch" ]; then
  echo "branch: $branch"
fi

if command -v gh >/dev/null 2>&1; then
  prs="$(gh pr list --author @me --state open --json number,title --limit 5 2>/dev/null || echo '[]')"
  echo "open_prs: $prs"
fi
