# /replay — Replay a Prior Session

Replay a previously recorded Claude Code session by extracting its JSONL transcript into readable markdown.

Usage: `/replay <session-id-or-path> [flags]`

The first argument is a session UUID, a prefix (≥4 chars), or an absolute path to a `.jsonl` file. Session files live at `~/.claude/projects/<slugified-cwd>/<session-id>.jsonl`; the extractor searches across all projects automatically.

## Step 1: Run the extractor

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/extract-session.py" $ARGUMENTS
```

By default, the output contains only the human conversation — user turns and assistant text — with harness noise (system reminders, local-command wrappers) stripped. Tool calls, tool results, thinking blocks, and subagent sidechains are omitted unless requested.

Flags to pass after the session ID:

- `--tools` — include one-line summaries of tool calls
- `--tool-results` — include (truncated) tool results
- `--thinking` — include assistant thinking blocks
- `--sidechains` — include subagent conversations
- `--history` — interleave user prompts from `~/.claude/history.jsonl` (auto-enabled for folder-only sessions)
- `--no-history` — disable history.jsonl backfill (overrides auto-enable)
- `--full` — shortcut for `--tools --tool-results --thinking --sidechains`
- `--max-chars N` — truncation limit for tool results and thinking (default 400)
- `--verbatim` — keep `<system-reminder>` and similar tags instead of stripping
- `--raw` — plain text output, no markdown headers

Events from non-main sources are annotated in headers: `[sub: agent-<id>]` for subagent files and `[from history.jsonl]` for backfilled user prompts.

## Step 2: Handle ambiguity and errors

- **Ambiguous match**: if the extractor exits with "matches multiple sessions" and lists candidates, show the list to the user and ask them to pick one (usually by pasting the full path).
- **No match**: if the extractor exits with "no session matching", tell the user and suggest they list available sessions with `ls ~/.claude/projects/*/`.
- **Folder-only session**: these are sessions whose main transcript was deleted by the default 30-day cleanup but whose subagent files survived. The extractor automatically loads all `subagents/agent-*.jsonl` files, enables `--sidechains`, and pulls matching user prompts from `~/.claude/history.jsonl`. The resulting view is the closest reconstruction possible from the surviving data.
- **Index-only session**: if a session UUID has no transcript files at all but appears in `sessions-index.json`, the replay will show the session's AI-generated summary, creation date, branch, and original message count from the index.

## Step 3: Present the output

- If the output is short (a few hundred lines), show it inline, AND save it to `docs/replay-<short-id>.md`.
- If the output is large (many thousands of lines), save it to `docs/replay-<short-id>.md` and show the user a brief summary plus the file path, so the main context stays lean. Offer to surface specific turns on request.

## Notes

- The script is read-only; it never modifies the original JSONL.
- For retelling or summarizing a long session, prefer running the extractor first (small cost) and reading its output, rather than reading the raw JSONL (many MB of envelope noise).
