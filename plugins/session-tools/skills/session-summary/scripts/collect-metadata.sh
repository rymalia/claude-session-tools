#!/bin/bash
# Emit everything /session-summary needs in a single invocation. The skill
# pre-authorizes this exact path via ${CLAUDE_SKILL_DIR} in its allowed-tools,
# so no user allowlist entry is required. Output is key: value lines; missing
# fields are omitted so the caller can treat absence as "not applicable."
# Fields: now, project, branch, open_prs, and (Claude Code only) session_start,
# session_resume.

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

# Claude Code start/resume timestamps. The SessionStart hook persists these to
# $CLAUDE_ENV_FILE, which Claude Code sources as a preamble before every Bash
# command — so this pre-authorized call already sees them, and /session-summary
# needs no separate (unauthorized) `echo`. Absent under Codex, which supplies
# the same values via the SESSION_SUMMARY_METADATA block instead.
if [ -n "${SESSION_START_TIME:-}" ]; then
  echo "session_start: $SESSION_START_TIME"
fi
if [ -n "${SESSION_RESUME_TIME:-}" ]; then
  echo "session_resume: $SESSION_RESUME_TIME"
fi
