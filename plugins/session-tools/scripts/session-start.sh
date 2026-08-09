#!/bin/bash
# Dispatch the shared SessionStart hook to host-specific state handling.

set -u

if [ -n "${PLUGIN_ROOT:-}" ] && [ -n "${PLUGIN_DATA:-}" ]; then
  exec python3 "${PLUGIN_ROOT}/scripts/codex-session-state.py"
fi

if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  exec bash "${CLAUDE_PLUGIN_ROOT}/scripts/session-start-time.sh"
fi

echo "session-tools: unable to determine plugin host" >&2
exit 1
