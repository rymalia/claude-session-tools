# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **Claude Code plugin marketplace** named `rymalia-plugins`. It is declarative — no build, no tests, no package manager. Work consists of editing JSON manifests, Markdown command definitions, and a Bash hook script.

## Repository layout

- `.claude-plugin/marketplace.json` — marketplace manifest listing available plugins. Each entry's `source` points at a directory under `plugins/`.
- `plugins/<name>/.claude-plugin/plugin.json` — per-plugin manifest (name, version, description, author).
- `plugins/<name>/hooks/hooks.json` — hook registrations. Use `${CLAUDE_PLUGIN_ROOT}` to reference files inside the plugin.
- `plugins/<name>/commands/*.md` — slash command definitions. The filename (sans `.md`) becomes the command name.
- `plugins/<name>/scripts/` — shell scripts invoked by hooks.

When adding a new plugin, register it in both `marketplace.json` and its own `plugin.json`, and bump the version in both places together.

## The `session-tools` plugin

Provides three slash commands (`/now`, `/session-summary`, `/replay`) and one `SessionStart` hook that captures session timestamps.

### How the timestamp mechanism works

`scripts/session-start-time.sh` is run by the `SessionStart` hook and reads a JSON payload from stdin. The `source` field drives behavior:

| `source`        | Effect                                                                 |
|-----------------|------------------------------------------------------------------------|
| `startup`/`clear` | Set `SESSION_START_TIME` to now, clear `SESSION_RESUME_TIME`.         |
| `resume`        | Preserve `SESSION_START_TIME`; append current time to `SESSION_RESUME_TIME` as a comma-separated list. |
| `compact`       | No-op — values are re-injected unchanged.                              |

The script persists values by appending `export` lines to `$CLAUDE_ENV_FILE` (so they survive as real env vars for the whole session), then also prints `KEY=VALUE` lines to stdout so they appear in the model's context. Downstream commands like `/session-summary` read them back with `echo $SESSION_START_TIME`.

If you modify this script, preserve both behaviors — the `CLAUDE_ENV_FILE` write (for persistence) *and* the stdout echo (for immediate context injection).

### `/session-summary` contract

The command requires timestamps to come from `SESSION_START_TIME`, `SESSION_RESUME_TIME`, or `/now` — **never estimated**. Output path is `docs/session-summary-YYYY-MM-DD-<short-descriptor>.md` with YAML frontmatter (`date`, `time`, optional `resumed`/`branch`/`related_pr`, `project`). Omit optional frontmatter fields entirely rather than leaving them blank.

### `/replay` contract

Wraps `scripts/extract-session.py`, which parses a session's JSONL transcript (`~/.claude/projects/<slug>/<session-id>.jsonl`) and emits only the conversational events (`user` + `assistant`), stripping `progress`, `file-history-snapshot`, and `system` noise. Harness wrappers like `<system-reminder>` and `<local-command-caveat>` are stripped by default; `<command-name>/cmd</command-name>` is collapsed to a one-line marker.

The extractor accepts a full UUID, a prefix (≥4 chars), or an absolute path. If a prefix is ambiguous (same session ID exists under multiple cwd slugs — common when a subdirectory was created mid-session), it lists candidates and exits non-zero. Flags are described in `commands/replay.md`. The script is Python 3 stdlib-only (no deps) and read-only.

**Storage-format eras.** Claude Code has persisted sessions under `~/.claude/projects/<slug>/` in at least three shapes:

| Era | Layout | Extractor behavior |
|-----|--------|--------------------|
| Old | `<uuid>/subagents/agent-*.jsonl` only (no main transcript) | Loads every subagent file, tags events with `[sub: <stem>]`, auto-enables `--sidechains`, and auto-enables `--history` to interleave user prompts from `~/.claude/history.jsonl`. This is the closest reconstruction possible after the main transcript was cleaned up. |
| Middle | `<uuid>.jsonl` + companion `<uuid>/` dir with `subagents/`, `tool-results/` | Main transcript extracts normally; companion subagent files accessible by explicit path. |
| New | `<uuid>.jsonl` only | Main transcript extracts normally. |

Subagent transcripts (path contains `/subagents/` or filename starts with `agent-`) are entirely `isSidechain: true` events — the extractor detects this and auto-enables `--sidechains`, so the caller doesn't need the flag just to see any output.

**history.jsonl backfill.** `~/.claude/history.jsonl` is a project-independent log of raw user prompts keyed by `sessionId`. It survives `cleanupPeriodDays`. `--history` interleaves its entries into the event stream by timestamp; for paired sessions the merger dedups against main-transcript user turns by normalized-text prefix. Auto-enabled for folder-only sessions; explicit `--no-history` disables even when auto-conditions apply.

**sessions-index.json metadata.** Each project directory may contain a `sessions-index.json` file with per-session metadata (`summary`, `firstPrompt`, `messageCount`, `created`, `modified`, `gitBranch`). This index survives cleanup even when all transcript files are deleted. The extractor enriches the replay header with index metadata when available, and as a last resort can resolve a UUID that has no `.jsonl` or folder by scanning all project indexes.

## Testing changes

There is no test suite. To exercise changes:

1. Reload the plugin in a Claude Code session (restart, or re-install from the marketplace path).
2. For the `SessionStart` hook, start a fresh session and verify `SESSION_START_TIME` appears in context; resume the session and verify `SESSION_RESUME_TIME` accumulates.
3. For command edits, invoke the slash command and confirm the behavior described in the `.md` file.

## Git policy (inherited from parent `CLAUDE.md`)

Never run `git commit`. Suggest the commit message and let the user commit.
