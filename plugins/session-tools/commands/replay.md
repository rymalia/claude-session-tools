# /replay — Replay a Prior Session

Replay a previously recorded **Claude Code** or **OpenAI Codex CLI** session by extracting its JSONL transcript into readable markdown.

Usage: `/replay <session-id-or-path> [flags]`

The first argument is a session UUID, a prefix (≥4 chars), or an absolute path to a `.jsonl` file. The extractor auto-detects the transcript format by content — no flag needed:

- **Claude Code** sessions live at `~/.claude/projects/<slugified-cwd>/<session-id>.jsonl`; the extractor searches across all projects automatically.
- **OpenAI Codex** sessions live at `~/.codex/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl`; a bare Codex UUID/prefix is matched against that tree (a Codex lookup never poaches a Claude UUID — Claude wins when both could match). A full path to a Codex `.jsonl` always works.

## Step 1: Run the extractor

This command **always saves its output to a file** — never print the replay only to the conversation. Pass `--save-dir docs` so the extractor writes the result to a file and reports the path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/extract-session.py" $ARGUMENTS --save-dir docs
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
- `--embed-images` — embed images inline as base64 `data:` URIs so they render in the markdown (default is a lean `[Image #N: <media_type>]` placeholder); ignored in `--raw`
- `--save-dir DIR` — write to a flag-derived, non-clobbering file in `DIR` (created if missing) and print the saved path instead of dumping to stdout

Events from non-main sources are annotated in headers: `[sub: agent-<id>]` for subagent files and `[from history.jsonl]` for backfilled user prompts.

### Output filename

When `--save-dir` is given, the extractor names the file `replay-<short-id>[-<flags>].md`, where `<short-id>` is the first 8 characters of the session UUID and `<flags>` reflects the view flags used, in a fixed canonical order (so `--verbatim --full` and `--full --verbatim` both yield the same name):

| Command | File written |
|---------|--------------|
| `/replay c506e1c6…` | `docs/replay-c506e1c6.md` |
| `/replay c506e1c6… --full` | `docs/replay-c506e1c6-full.md` |
| `/replay c506e1c6… --verbatim --full` | `docs/replay-c506e1c6-verbatim-full.md` |
| `/replay c506e1c6… --tools --max-chars 200` | `docs/replay-c506e1c6-tools-max200.md` |

Existing files are **never overwritten**: a successive run of the same command writes `…-2.md`, `…-3.md`, and so on. The extractor handles naming and collision avoidance itself — do not construct the filename yourself.

## Step 2: Handle ambiguity and errors

- **Ambiguous match**: if the extractor exits with "matches multiple sessions" and lists candidates, show the list to the user and ask them to pick one (usually by pasting the full path).
- **No match**: if the extractor exits with "no session matching", tell the user and suggest they list available sessions with `ls ~/.claude/projects/*/`.
- **Folder-only session**: these are sessions whose main transcript was deleted by the default 30-day cleanup but whose subagent files survived. The extractor automatically loads all `subagents/agent-*.jsonl` files, enables `--sidechains`, and pulls matching user prompts from `~/.claude/history.jsonl`. The resulting view is the closest reconstruction possible from the surviving data.
- **Index-only session**: if a session UUID has no transcript files at all but appears in `sessions-index.json`, the replay will show the session's AI-generated summary, creation date, branch, and original message count from the index.

## Step 3: Present the output

The extractor has already written the file (Step 1) and printed a `saved: <path> (N turns, M lines)` line. Always report that path to the user.

The extraction itself is deterministic Python — no model reasoning is involved, so it costs nothing regardless of which model invoked the command. The only expensive step is **reading the saved file back into context to summarize or comment on it**. Route that step by size and by whether the user actually asked for a summary:

- **File only (no summary requested).** Just report the `saved:` path. Do not read the file — nobody needs it in context.
- **Short replay (a few hundred lines).** `Read` the saved file directly and show it inline or summarize as asked. No subagent — the round-trip and hand-off overhead would cost more than reading it yourself.
- **Large replay (many thousands of lines) *and* a summary/commentary is wanted.** Do **not** `Read` the raw file into this (frontier) context. Instead delegate the bulk read to a **Sonnet subagent** (`Agent` tool, `subagent_type: general-purpose`, `model: sonnet`): have it Read the saved file and return a compact digest (key turns, decisions, outcome). Then add your commentary on the *digest*, keeping the multi-thousand-line transcript out of this context entirely. Offer to surface specific turns on request.

Delegating the read spends cheap tokens on the large mechanical read and reserves this context for synthesis and commentary. The gate is not "which model processes the transcript" (the Python does that); it is "does anything need to read the extracted file into a frontier context, and if so, how big is it?"

## Codex sessions

Codex transcripts use a different on-disk shape — every line is a `{timestamp, type, payload}` envelope — but the extractor converts the conversational records into the same internal form as Claude sessions, so all flags, filenames, and `--save-dir` behavior are identical. The header shows `format: OpenAI Codex CLI rollout (vX)` and the model. Codex-specific behavior:

- **Reasoning is encrypted.** Codex persists reasoning as opaque `encrypted_content` with no plaintext, so `--thinking` (and `--full`) renders a `> _reasoning:_ [encrypted by Codex]` placeholder per block rather than the actual reasoning. Plaintext is shown only on the rare occasion a summary is present.
- **`--verbatim` is effectively a no-op** for Codex: it only suppresses Claude-specific harness-tag stripping (`<system-reminder>`, `<local-command-*>`), and Codex transcripts don't contain those tags. The output matches `--full`; the filename still distinguishes them.
- **`--history` and `--sidechains` don't apply** — Codex has no `~/.claude/history.jsonl` equivalent and no subagent sidechain files in this format.
- The clean user-typed prompt comes from Codex's `event_msg/user_message`; harness-injected context (AGENTS.md, environment) and the duplicate `agent_message` event stream are dropped.

## Notes

- The script is read-only; it never modifies the original JSONL.
- **Images** in a prompt render as a lean `[Image #N: <media_type>]` placeholder by default. Pass `--embed-images` to inline the full picture as a base64 `data:` URI (decoded from the transcript, since the harness `image-cache` file is ephemeral) so it displays directly in the saved markdown — at the cost of ~33% size overhead per image. `--raw` mode always uses the placeholder regardless, to avoid swamping plain-text output.
- For retelling or summarizing a long session, prefer running the extractor first (small cost) and reading its output, rather than reading the raw JSONL (many MB of envelope noise).
