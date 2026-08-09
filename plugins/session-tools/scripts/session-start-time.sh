#!/bin/bash
# Capture session timestamps and make them available throughout the session.
#
# Behavior by SessionStart source:
#   startup/clear: set SESSION_START_TIME, clear SESSION_RESUME_TIME
#   resume:        set/accumulate SESSION_RESUME_TIME, preserve SESSION_START_TIME
#   compact:       re-inject existing values unchanged
#
# Reads JSON from stdin to determine the source field.
#
# Not captured here (native Claude Code features cover them, as of the plugin's
# latest-client-only support policy):
#   - the session id: /session-summary reads the native ${CLAUDE_SESSION_ID}
#     template variable directly.
#   - the plugin root: /session-summary references bundled scripts via the native
#     ${CLAUDE_SKILL_DIR} variable, which also authorizes them in allowed-tools,
#     so no version-stable SESSION_TOOLS_ROOT export (and no allowlist entry) is
#     needed.

INPUT=$(cat)
SOURCE=$(echo "$INPUT" | jq -r '.source // "startup"')
TS=$(date '+%Y-%m-%d %I:%M %p %Z')

case "$SOURCE" in
  startup|clear)
    SESSION_START_TIME="$TS"
    SESSION_RESUME_TIME=""
    echo "export SESSION_START_TIME='$SESSION_START_TIME'" >> "$CLAUDE_ENV_FILE"
    echo "export SESSION_RESUME_TIME=''" >> "$CLAUDE_ENV_FILE"
    ;;
  resume)
    if [ -z "$SESSION_START_TIME" ]; then
      SESSION_START_TIME="$TS"
      echo "export SESSION_START_TIME='$SESSION_START_TIME'" >> "$CLAUDE_ENV_FILE"
    fi
    if [ -n "$SESSION_RESUME_TIME" ]; then
      SESSION_RESUME_TIME="$SESSION_RESUME_TIME, $TS"
    else
      SESSION_RESUME_TIME="$TS"
    fi
    echo "export SESSION_RESUME_TIME='$SESSION_RESUME_TIME'" >> "$CLAUDE_ENV_FILE"
    ;;
  compact)
    # Re-inject only — no new timestamps
    ;;
esac

# Inject into context
echo "SESSION_START_TIME=$SESSION_START_TIME"
if [ -n "$SESSION_RESUME_TIME" ]; then
  echo "SESSION_RESUME_TIME=$SESSION_RESUME_TIME"
fi
