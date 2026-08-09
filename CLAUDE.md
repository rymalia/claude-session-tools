# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A dual-host **Claude Code and OpenAI Codex plugin marketplace** named `rymalia-plugins`. It is declarative — no build, no package manager, and only focused script validation. Work consists of editing JSON manifests, Markdown command or skill definitions, and session hook scripts.

## Repository layout

- `.claude-plugin/marketplace.json` — marketplace manifest listing available plugins. Each entry's `source` points at a directory under `plugins/`.
- `.agents/plugins/marketplace.json` — repo-local Codex marketplace manifest.
- `plugins/<name>/.claude-plugin/plugin.json` — per-plugin manifest (name, version, description, author).
- `plugins/<name>/.codex-plugin/plugin.json` — Codex plugin manifest and bundled-skill metadata.
- `plugins/<name>/hooks/hooks.json` — shared hook registrations. Codex provides `${CLAUDE_PLUGIN_ROOT}` as a compatibility alias.
- `plugins/<name>/commands/*.md` — slash command definitions. The filename (sans `.md`) becomes the command name.
- `plugins/<name>/skills/*/SKILL.md` — Codex skill definitions.
- `plugins/<name>/scripts/` — shell scripts invoked by hooks.

Keep the `session-tools` version synchronized across `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`, and `.codex-plugin/plugin.json`.

## The `session-tools` plugin

Provides Claude slash commands, Codex skills, transcript replay for both session formats, and one shared `SessionStart` hook that captures host-specific session metadata.

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

`scripts/session-start.sh` is run by the shared `SessionStart` hook and dispatches by host. Claude Code continues to use `scripts/session-start-time.sh`, which reads a JSON payload from stdin. The `source` field drives behavior:

| `source`        | Effect                                                                 |
|-----------------|------------------------------------------------------------------------|
| `startup`/`clear` | Set `SESSION_START_TIME` to now, clear `SESSION_RESUME_TIME`.         |
| `resume`        | Preserve `SESSION_START_TIME`; append current time to `SESSION_RESUME_TIME` as a comma-separated list. |
| `compact`       | No-op — values are re-injected unchanged.                              |

The script also extracts `session_id` from the hook payload and persists it as `CLAUDE_SESSION_ID` (re-captured on every source so resume/compact keep it fresh). This is the UUID naming the JSONL transcript at `~/.claude/projects/<slug>/<id>.jsonl` — the same id `/replay` consumes — and `/session-summary` stamps it into frontmatter.

The script persists values by appending `export` lines to `$CLAUDE_ENV_FILE` (so they survive as real env vars for the whole session), then also prints `KEY=VALUE` lines to stdout so they appear in the model's context. Downstream commands like `/session-summary` read them back with `echo $SESSION_START_TIME`.

If you modify this script, preserve both behaviors — the `CLAUDE_ENV_FILE` write (for persistence) *and* the stdout echo (for immediate context injection).

### Codex session-summary support

Codex loads `skills/session-summary/SKILL.md` as `$session-summary`. On `SessionStart`, the dispatcher detects Codex through `PLUGIN_ROOT`/`PLUGIN_DATA` and runs `scripts/codex-session-state.py`. The Python script is standard-library only and stores one JSON state file per session under `$PLUGIN_DATA/session-summary/`.

Codex sources behave as follows:

| `source` | Effect |
|----------|--------|
| `startup`/`clear` | Record the exact start time and clear resume timestamps. |
| `resume` | Preserve the stored start time and append the exact resume time. |
| `compact` | Re-inject stored metadata without changing timestamps. |

The hook emits `SESSION_SUMMARY_METADATA` as additional developer context. The skill combines it with one call to `scripts/collect-metadata.sh`, then writes the same summary structure as the Claude command. If the hook was not trusted or no state exists, the skill leaves the start time blank rather than parsing Codex rollout files or estimating it.

Codex discovers `hooks/hooks.json` automatically from the plugin root. Installed hooks must be reviewed and trusted through `/hooks` before they run.

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

### `/replay-merge` contract

`scripts/merge-sessions.py` renders **two or more** sessions as one timestamp-sorted timeline. It imports `extract-session.py` as a sibling module (via `importlib`) and reuses its resolution, loading, and rendering wholesale — the merger only pools events, badges each by origin (`A·<short8>`, `B·…`), and splices those badges into the headers `render_event` produces. Because it delegates resolution per-argument, **a merge can mix Claude Code and OpenAI Codex sessions freely** — each positional is run through `resolve_codex_path` first (Codex) then `resolve_session` (Claude), exactly as the single-session `main()` does, and Codex sessions are badged with their CLI version.

The merge path has its own `main()`/argparse, so it must be kept in lock-step with feature work on `/replay`'s argparse layer (the shared *renderer* is inherited automatically; the *CLI layer* is not). Parity items that had to be mirrored explicitly: `--embed-images` must be threaded through `build_args` (the renderer reads `args.embed_images` directly, so its absence is an `AttributeError` on any image block, not a missing feature); `--save-dir` reuses the same flag-token vocabulary (`derive_flag_tokens`) but writes `replay-merge-<shortA>-<shortB>[…][-<flags>].md` via a merge-local non-clobbering path builder (the single-session `derive_output_path` hardcodes a `replay-<id>` stem). Merge has no `--history` (no cross-session concept) and adds `--models` to badge each assistant turn with its producing model. The command markdown (`commands/replay-merge.md`) follows the same always-save contract as `/replay` (`--save-dir docs`) and the same size/intent gating for whether to read the saved file back (delegating large-file reads to a Sonnet subagent).

## Testing changes

There is no test suite. To exercise changes:

1. Reload the plugin in a Claude Code session (restart, or re-install from the marketplace path).
2. For the `SessionStart` hook, start a fresh session and verify `SESSION_START_TIME` appears in context; resume the session and verify `SESSION_RESUME_TIME` accumulates.
3. For command edits, invoke the slash command and confirm the behavior described in the `.md` file.
4. For Codex changes, validate the skill and plugin manifests, then install from the repo marketplace in a new session. Review the hook through `/hooks`, start and resume a session, and confirm `SESSION_SUMMARY_METADATA` retains the original start time without treating compaction as a resume.

## Git policy (inherited from parent `CLAUDE.md`)

Never run `git commit`. Suggest the commit message and let the user commit.
