---
title: Claude Code Session Logging — Where It Lives, How Long It Stays, and What Controls It
date: 2026-04-15
audience: Claude Code users (interactive CLI, IDE extensions, Agent SDK)
topics: [session-persistence, jsonl-format, cleanup, retention]
tldr: >
  By default, Claude Code deletes session transcripts 30 days after their last
  modification via the `cleanupPeriodDays` setting. Subagent transcripts under
  `<session>/subagents/` are NOT covered by this cleanup, which leaves
  "folder-only" orphans that most viewers (including Claude Code Viewer) cannot
  read. To retain transcripts indefinitely, we set `cleanupPeriodDays` to a large
  value (e.g. `3650`) in `~/.claude/settings.json`.
sources:
  - https://code.claude.com/docs/en/claude-directory
  - https://code.claude.com/docs/en/settings
  - https://code.claude.com/docs/en/env-vars
---

# Claude Code Session Logging

This is a reference for anyone who wants to understand (a) where Claude Code stores the data from your coding sessions, (b) how long it keeps that data, and (c) which settings affect retention. It also includes a short JSONL-format section for anyone who wants to parse their own transcripts.

Written in response to discovering — the hard way — that Claude Code silently deletes conversation transcripts after 30 days by default.

## TL;DR

If you care about your session history beyond the last month, add this to `~/.claude/settings.json`:

```json
{
  "cleanupPeriodDays": 3650
}
```

That bumps retention from the 30-day default to ~10 years, effectively "forever." The setting is read at Claude Code startup; next launch it takes effect.

If you don't, every session's full transcript is deleted 30 days after its last modification. User prompts (stored separately in `history.jsonl`) and subagent transcripts (stored in subdirectories) survive the cleanup — but the main conversation is gone.

## Where session data lives

Everything Claude Code writes about a session lives under `~/.claude/`. The relevant paths:

| Path | Contents |
|------|----------|
| `~/.claude/projects/<slug>/<session-id>.jsonl` | **Main transcript**: every user message, assistant message, tool call, tool result, and internal event for the session |
| `~/.claude/projects/<slug>/<session-id>/tool-results/` | Large tool outputs spilled to separate files |
| `~/.claude/projects/<slug>/<session-id>/subagents/agent-*.jsonl` | Per-subagent transcripts (one file per Task-tool invocation) |
| `~/.claude/history.jsonl` | Every prompt you've ever typed, with timestamp + project path. Used for up-arrow recall. |
| `~/.claude/file-history/<session-id>/` | Pre-edit snapshots of files Claude modified (used by `/rewind` checkpoint restore) |
| `~/.claude/plans/` | Plan files written during plan mode |
| `~/.claude/debug/` | Per-session debug logs (written only with `--debug` or `/debug`) |
| `~/.claude/paste-cache/`, `~/.claude/image-cache/` | Large pastes and attached images |
| `~/.claude/session-env/` | Per-session environment metadata (not human-readable) |
| `~/.claude/todos/` | Legacy per-session task lists; not written by current versions |

The `<slug>` is a slugified form of the working directory at the time the session started. For example, a session started from `/Users/ryan/projects/bird` would land under `~/.claude/projects/-Users-ryan-projects-bird/`.

## Retention: what gets deleted, and when

Claude Code runs a cleanup pass **on startup**. It deletes files whose last-modified time is older than `cleanupPeriodDays` (default: 30).

### Auto-cleaned

These paths are cleaned up:

- `projects/<slug>/<session-id>.jsonl` — the main transcript
- `projects/<slug>/<session-id>/tool-results/` — spilled tool outputs
- `file-history/<session-id>/`
- `plans/`
- `debug/`
- `paste-cache/`, `image-cache/`
- `session-env/`

### Kept until you delete them

These paths are **not** covered by automatic cleanup:

- `history.jsonl` — your prompts, indefinitely
- `stats-cache.json` — aggregated token/cost counts
- `backups/` — config backups
- `todos/` — legacy, safe to delete manually

### The asymmetry that creates "folder-only" sessions

Critically, `projects/<slug>/<session-id>/subagents/` — the directory holding per-subagent transcripts — is **not listed among the auto-cleaned paths**. Neither the docs nor any readable comment explains why.

The practical effect: when a session passes the 30-day cutoff, its main transcript (`<session-id>.jsonl`) gets deleted, but the sibling directory (`<session-id>/subagents/`) with its `agent-*.jsonl` files survives. You're left with a folder that looks like a session but lacks the main conversation.

This state is effectively invisible to most downstream viewers:

- **Claude Code Viewer (CCV)**: its session discovery requires a `.jsonl` file at the project-dir root. Folder-only sessions don't appear in its UI.
- **Kuato**: its parser walks `*.jsonl` files — folder-only sessions are silently skipped.
- **Claude Code itself**: `--resume` / `--continue` can't restore these sessions.

If you use subagents heavily (Task tool, specialized agents, etc.), a large fraction of your older work history may be in this state right now.

## How to control retention

### Keep transcripts longer (or indefinitely)

`cleanupPeriodDays` — in `~/.claude/settings.json`:

```json
{
  "cleanupPeriodDays": 3650
}
```

- Default: `30` days
- Minimum: `1` day (must be at least 1; `0` is rejected as a validation error to prevent accidental total disablement)
- No documented maximum. `3650` (~10 years) is a safe "effectively forever" value.
- Must be in user settings (`~/.claude/settings.json`), not project-level, if you want it applied across all sessions.

Applies to: `projects/`, `file-history/`, `plans/`, `debug/`, `paste-cache/`, `image-cache/`, `session-env/`.

### Stop writing transcripts entirely (for ephemeral sessions)

Three options, depending on how you invoke Claude Code:

| Mechanism | Scope | Syntax |
|-----------|-------|--------|
| `CLAUDE_CODE_SKIP_PROMPT_HISTORY` environment variable | Any invocation mode | `export CLAUDE_CODE_SKIP_PROMPT_HISTORY=1` before `claude` |
| `--no-session-persistence` CLI flag | Non-interactive mode (`-p`) only | `claude -p "…" --no-session-persistence` |
| `persistSession: false` SDK option | Agent SDK apps | `query({ prompt, options: { persistSession: false } })` |

When set, the session doesn't appear in `--resume`, `--continue`, or up-arrow history. Useful for scripted runs that process secrets or pastes you don't want persisted.

### Manually clear old data

Every auto-cleaned path is also safe to delete by hand. The docs spell out what you lose:

| Delete | You lose |
|--------|----------|
| `~/.claude/projects/` | Resume / continue / rewind for past sessions |
| `~/.claude/history.jsonl` | Up-arrow prompt recall |
| `~/.claude/file-history/` | Checkpoint restore for past sessions |
| `~/.claude/stats-cache.json` | Historical `/cost` totals |
| `~/.claude/debug/`, `plans/`, `paste-cache/`, `image-cache/`, `session-env/` | Nothing user-facing |
| `~/.claude/todos/` | Nothing — legacy directory |

**Do not delete:** `~/.claude.json`, `~/.claude/settings.json`, `~/.claude/plugins/`. These hold your auth, preferences, and installed plugins.

### Security note

Transcripts are stored **in plaintext**. Anything that passed through a tool — file contents, command output, pasted text, environment values — is written verbatim to `projects/<slug>/<session-id>.jsonl`. OS file permissions are the only protection. If you routinely work with credentials, either:

- Lower `cleanupPeriodDays` to shorten the exposure window
- Use `CLAUDE_CODE_SKIP_PROMPT_HISTORY` for sessions that handle secrets
- Configure `permissions.deny` to block reads of sensitive files before they reach a transcript

## JSONL format

Each session's main transcript is one JSON object per line (`.jsonl`). The file contains a mix of event types — only some are conversational.

### Event types observed

| `type` | Meaning |
|--------|---------|
| `user` | User message, tool-result payload, or slash-command invocation |
| `assistant` | Model output: text, thinking, or tool_use blocks |
| `progress` | Internal tooling heartbeats (e.g. subagent progress) |
| `file-history-snapshot` | Snapshot pointer for `/rewind` |
| `system` | Hook events, local-command wrappers, compact/turn-duration markers, API errors |
| `queue-operation` | Internal queue bookkeeping |
| `last-prompt` | Marker for last-prompt bookkeeping |

For reading a conversation, only `user` and `assistant` matter. Everything else is implementation detail.

### User event shape

```json
{
  "type": "user",
  "timestamp": "2026-03-25T23:17:38.123Z",
  "sessionId": "...",
  "isSidechain": false,
  "message": { "role": "user", "content": "..." }
}
```

`message.content` is overloaded:

- **Plain string**: a real user message typed at the prompt (or a slash-command wrapper like `<command-name>/copy</command-name>` when the user invokes a local command).
- **Array of `tool_result` blocks**: when Claude's tool call returns output, the harness injects it back into the conversation as a synthetic user message. Same `type: "user"`, but semantically a tool return, not human input.

Shape for tool results:

```json
"content": [
  {
    "type": "tool_result",
    "tool_use_id": "...",
    "content": "<text or array of {type:'text',text:'...'}>"
  }
]
```

Parsers that equate `type: "user"` with "human input" will misclassify half the user events. Discriminate by inspecting `content`'s shape.

### Assistant event shape

```json
{
  "type": "assistant",
  "timestamp": "2026-03-25T23:17:43.456Z",
  "sessionId": "...",
  "isSidechain": false,
  "message": {
    "role": "assistant",
    "model": "claude-opus-4-6",
    "content": [
      { "type": "text",     "text": "..." },
      { "type": "thinking", "thinking": "...", "signature": "..." },
      { "type": "tool_use", "id": "...", "name": "Read", "input": { "file_path": "..." } }
    ],
    "usage": { "input_tokens": 123, "output_tokens": 456, "...": "..." }
  }
}
```

`message.content` is always an array of blocks. Types: `text` (visible model output), `thinking` (internal reasoning, usually not shown to the user), `tool_use` (a tool invocation with name + input).

### isSidechain

Every event carries `isSidechain: boolean`. `false` for the main conversation, `true` for subagent events.

- In a paired session (`<uuid>.jsonl` + `<uuid>/subagents/`), main-conversation events live in the `.jsonl` with `isSidechain: false`, and subagent events live in the per-agent files with `isSidechain: true`.
- In a folder-only session (subagents survived cleanup but main transcript was deleted), all events have `isSidechain: true` because only subagent files remain.

A parser that filters out sidechain events by default will produce **zero output** on a folder-only session. Useful to auto-detect: if the input path is `.../subagents/agent-*.jsonl` or `parent.name == "subagents"`, treat all events as signal.

### Harness wrappers in user text

User messages often contain system-generated tags that are noise for anyone reading the transcript conversationally:

- `<system-reminder>...</system-reminder>` — harness reminders to the model
- `<local-command-caveat>...</local-command-caveat>` — auto-inserted when a slash command is invoked
- `<command-name>/foo</command-name>`, `<command-message>`, `<command-args>` — slash-command invocation markers
- `<local-command-stdout>`, `<local-command-stderr>` — captured output from `!`-prefixed shell commands

For a clean read, strip these. For debugging a hook or slash command, keep them.

## Recovering (or at least salvaging) old sessions

When a main transcript is gone but the `subagents/` folder survives, you can still reconstruct a meaningful portion of what happened:

| Source | What it gives you |
|--------|-------------------|
| `~/.claude/history.jsonl` | All user prompts you typed for that session (timestamps + project + text) |
| `<session-id>/subagents/agent-*.jsonl` | Full transcripts of each subagent's delegated task |
| `~/.claude/file-history/<session-id>/` (if within `cleanupPeriodDays`) | Pre-edit file snapshots |
| Your own git log | What actually shipped from that session |

What's genuinely lost is the main assistant's non-tool text — the conversational glue between your prompts and the subagent invocations. If you used subagents heavily, you still have most of the substance. If the session was a pure pair-programming conversation with no subagents, you have only your prompts plus whatever edits landed in git.

A simple extractor that cross-references `history.jsonl` by session ID and concatenates `subagents/*.jsonl` by timestamp gets you most of the way back. The `session-tools` plugin in this repo contains such a tool (`/replay`).

## References

Official Claude Code documentation:

- [Claude directory reference](https://code.claude.com/docs/en/claude-directory) — canonical description of what lives under `~/.claude/` and what's auto-cleaned
- [Settings reference](https://code.claude.com/docs/en/settings) — full `cleanupPeriodDays` description and all other `settings.json` fields
- [Environment variables reference](https://code.claude.com/docs/en/env-vars) — full `CLAUDE_CODE_SKIP_PROMPT_HISTORY` description and related vars
- [CLI reference](https://code.claude.com/docs/en/cli-reference) — `--no-session-persistence` and other launch flags

Community tools that parse these JSONL files (useful context, not required reading):

- **Claude Code Viewer** — web UI for reading sessions (assumes `.jsonl` present; does not surface folder-only sessions)
- **Kuato** — session memory / recall CLI (extracts user messages as search signal; does not handle folder-only sessions)
- **session-tools** (`/replay`, this repo) — lightweight extractor that surfaces folder-only sessions and degrades gracefully when the main transcript is missing

## Changelog of this information

Entries from the Claude Code changelog (`@anthropic-ai/claude-code` on npm), with release dates:

| Version | Date | Entry |
|---------|------|-------|
| `0.2.117` | May 2025 | "Introduced `settings.cleanupPeriodDays`" — the feature was created. This was in the earliest era of Claude Code; the default was already 30 days. |
| `2.1.83` | March 2026 | "Fixed tool result files never being cleaned up, ignoring the `cleanupPeriodDays` setting" — confirms `tool-results/` is now part of the cleanup. Prior to this fix, only the main transcript was cleaned; spilled tool results accumulated indefinitely. |
| `2.1.89` | March 2026 | "Changed `cleanupPeriodDays: 0` in settings.json to be rejected with a validation error — it previously silently disabled transcript persistence" — `0` is not a valid "disable" value; set a high number instead. |
| `2.1.101` | April 2026 | "Fixed `--setting-sources` without `user` causing background cleanup to ignore `cleanupPeriodDays` and delete conversation history older than 30 days" — confirms the 30-day default applies when user settings aren't consulted. |

The feature has been actively maintained for nearly a year (May 2025 – April 2026) with three bug fixes. It is clearly intentional behavior, not an accident.
