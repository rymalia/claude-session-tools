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

### Required permissions (first-run setup)

`/session-summary` needs a single allowlist entry. `/now` is a separate standalone command and needs its own entry if you plan to use it on its own.

| Command | Used by | Allowlist entry |
|---------|---------|-----------------|
| `bash "$SESSION_TOOLS_ROOT/scripts/collect-metadata.sh"` | `/session-summary` (end-time, project, branch, open PRs) | `Bash(bash "$SESSION_TOOLS_ROOT/scripts/collect-metadata.sh")` |
| `date '+%Y-%m-%d %I:%M %p %Z'` | `/now` standalone (NOT invoked by `/session-summary`) | `Bash(date:*)` |

Add to the `permissions.allow` array in `~/.claude/settings.json` (user-level, so they apply in any project). Both are read-only.

**Why `/session-summary` no longer invokes `/now`.** When Claude Code surfaces slash commands as skills, they are namespaced by plugin (`session-tools:now`). Invoking a bare `/now` from inside another command's markdown was fragile — the LLM occasionally rendered it as `Skill(now)` and hit "Unknown skill: now." To avoid the cross-command dependency, the metadata script emits `now: <timestamp>` as its first line. `/now` remains a useful standalone command; it just isn't called from `/session-summary` anymore.

The remaining shells in `/session-summary` (`echo $SESSION_START_TIME`, `echo $SESSION_RESUME_TIME`) are covered by the common `Bash(echo:*)` entry most users already have.

**Why the allowlist entry uses a literal `$SESSION_TOOLS_ROOT`.** Claude Code matches permission strings against the **pre-expansion** command text, not the resolved path. `${CLAUDE_PLUGIN_ROOT}` embeds the plugin version, so an exact-path allow would break on every upgrade. The `SessionStart` hook persists `SESSION_TOOLS_ROOT` to `$CLAUDE_ENV_FILE`, and the `/session-summary` command invokes the script via that var — so the allowlist string stays stable across plugin versions.

**Why settings cascade matters here.** Claude Code merges allowlists from `~/.claude/settings.json` → `~/.claude/settings.local.json` → `<cwd>/.claude/settings.json` → `<cwd>/.claude/settings.local.json`. It does **not** walk up from `<cwd>` through parent directories. Permissions added to `~/projects/.claude/settings.local.json` only apply when `~/projects` is itself the cwd, not when a subdirectory is. Because `/session-summary` is designed to run in any project, put its permissions at the user level.

### Metadata collection script

`scripts/collect-metadata.sh` bundles `date`, `basename "$PWD"`, `git branch --show-current`, and `gh pr list ...` into a single invocation. Output is `key: value` lines: `now:` (always), `project:` (always), `branch:` (omitted if not a git repo), `open_prs:` (omitted if `gh` isn't installed). If you add a new field to the `/session-summary` frontmatter, prefer extending this script over adding a second shell-out — keep the command to one permission surface.

### How the timestamp mechanism works

`scripts/session-start-time.sh` is run by the `SessionStart` hook and reads a JSON payload from stdin. The `source` field drives behavior:

| `source`        | Effect                                                                 |
|-----------------|------------------------------------------------------------------------|
| `startup`/`clear` | Set `SESSION_START_TIME` to now, clear `SESSION_RESUME_TIME`.         |
| `resume`        | Preserve `SESSION_START_TIME`; append current time to `SESSION_RESUME_TIME` as a comma-separated list. |
| `compact`       | No-op — values are re-injected unchanged.                              |

The script also extracts `session_id` from the hook payload and persists it as `CLAUDE_SESSION_ID` (re-captured on every source so resume/compact keep it fresh). This is the UUID naming the JSONL transcript at `~/.claude/projects/<slug>/<id>.jsonl` — the same id `/replay` consumes — and `/session-summary` stamps it into frontmatter.

The script persists values by appending `export` lines to `$CLAUDE_ENV_FILE` (so they survive as real env vars for the whole session), then also prints `KEY=VALUE` lines to stdout so they appear in the model's context. Downstream commands like `/session-summary` read them back with `echo $SESSION_START_TIME`.

If you modify this script, preserve both behaviors — the `CLAUDE_ENV_FILE` write (for persistence) *and* the stdout echo (for immediate context injection).

### `/session-summary` contract

The command requires timestamps to come from `SESSION_START_TIME`, `SESSION_RESUME_TIME`, or `/now` — **never estimated**. Output path is `docs/session-summary-YYYY-MM-DD-<short-descriptor>.md` with YAML frontmatter (`date`, `time`, `project`, optional `session_id`/`resumed`/`branch`/`related_pr`). The `session_id` comes from `CLAUDE_SESSION_ID` (injected by the SessionStart hook). Omit optional frontmatter fields entirely rather than leaving them blank.

### `/replay` contract

Wraps `scripts/extract-session.py`, which parses a session's JSONL transcript (`~/.claude/projects/<slug>/<session-id>.jsonl`) and emits only the conversational events (`user` + `assistant`), stripping `progress`, `file-history-snapshot`, and `system` noise. Harness wrappers like `<system-reminder>` and `<local-command-caveat>` are stripped by default; `<command-name>/cmd</command-name>` is collapsed to a one-line marker.

User turns whose `content` is a **list of blocks** (not a bare string) — which is how the harness stores any prompt carrying an image or attachment — have their `text` blocks rendered too, so image-bearing prompts are not silently dropped. `image` blocks render as a short `[Image #N: <media_type>]` placeholder by default; `--embed-images` instead inlines a self-contained base64 `data:` URI (`![Image #N](data:image/…;base64,…)`) so the picture displays in any markdown viewer. The pixels come from the transcript's base64 (the `image-cache` PNG the harness references is ephemeral and often already deleted). `[Image #N]` is labeled from `imagePasteIds` to match the in-text marker the harness leaves in the prompt. `--raw` (plain text) always uses the placeholder regardless of `--embed-images`, since a multi-hundred-KB URI would swamp it. `isMeta` user events (harness-injected command-body expansions and `[Image: source: …]` refs) are suppressed unless `--verbatim` is set.

**Always-save contract.** The `/replay` command always passes `--save-dir docs`, so the extractor writes the replay to a file rather than only printing it. The filename is `replay-<short-id>[-<flags>].md`, where `<short-id>` is the first 8 chars of the session UUID and `<flags>` are the view flags in a fixed canonical order (so flag order on the command line doesn't change the name). Existing files are never overwritten — collisions get a `-2`, `-3`, … suffix. Naming and collision avoidance live in the script (`derive_flag_tokens` / `derive_output_path`), not in the command markdown.

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

**OpenAI Codex CLI support.** The extractor also replays Codex rollout transcripts, which live under `~/.codex/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl` and use a completely different shape: every line is a `{timestamp, type, payload}` envelope rather than a top-level role + `message`. Format is auto-detected by content (`is_codex_file` sniffs the envelope), so no `--codex` flag exists. A bare Codex UUID/prefix is resolved by `resolve_codex_path` globbing the Codex sessions tree; to avoid namespace collisions it only claims an id when the Claude tree has no matching `.jsonl` (Claude wins). The converter (`load_codex_events`) maps Codex records onto the **same Claude-shaped event dicts** the renderer already consumes, so all flags, filenames, and `--save-dir` logic are reused unchanged:

| Codex record | Rendered as | Flag gate |
|--------------|-------------|-----------|
| `event_msg/user_message` | user text turn | always |
| `response_item/message` role=assistant | assistant text turn | always |
| `response_item/function_call`, `custom_tool_call` | assistant `tool_use` one-liner | `--tools` |
| `response_item/function_call_output`, `custom_tool_call_output` | user `tool_result` | `--tool-results` |
| `response_item/reasoning` | `> _reasoning:_ [encrypted by Codex]` placeholder | `--thinking` |

Dropped as noise/duplication: `response_item/message` role in {user, developer} (harness-injected AGENTS.md/environment context and the system prompt), `event_msg/agent_message` (byte-identical to the assistant `response_item`), and bookkeeping (`token_count`, `task_started`/`task_complete`, `*_tool_call_end` echoes). Codex caveats: reasoning is encrypted (no plaintext, hence the placeholder); `--verbatim` is a no-op (no Claude harness tags to keep, so output matches `--full`); `--history`/`--sidechains` don't apply (no Codex equivalent). The header shows `format: OpenAI Codex CLI rollout (vX)` and the model.

## Testing changes

There is no test suite. To exercise changes:

1. Reload the plugin in a Claude Code session (restart, or re-install from the marketplace path).
2. For the `SessionStart` hook, start a fresh session and verify `SESSION_START_TIME` appears in context; resume the session and verify `SESSION_RESUME_TIME` accumulates.
3. For command edits, invoke the slash command and confirm the behavior described in the `.md` file.

## Git policy (inherited from parent `CLAUDE.md`)

Never run `git commit`. Suggest the commit message and let the user commit.
