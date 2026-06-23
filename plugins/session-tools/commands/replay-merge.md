# /replay-merge — Merge & Replay Multiple Sessions

Merge two or more prior Claude Code sessions into a single, timestamp-sorted replay. Every event from every named session is pooled and rendered in true chronological order, with each turn badged by its origin session — so sessions that ran in tandem (e.g. you relaying responses between two parallel agents) read as one coherent timeline.

Usage: `/replay-merge <id-or-path> <id-or-path> [<id-or-path> ...] [flags]`

Each positional argument is a session UUID, a prefix (≥4 chars), or an absolute path to a `.jsonl` file — resolved exactly like `/replay`. **At least two sessions are required**; for a single session use `/replay`.

## Step 1: Run the merger

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/merge-sessions.py" $ARGUMENTS
```

By default the output is conversation-only (user turns + assistant text), harness noise stripped — same as `/replay`. The merge-specific behavior: turns from all sessions are interleaved by timestamp, and each header carries an origin badge like `A·495d4d49`.

Flags (mirror `/replay`, plus one):

- `--tools` — include one-line tool-call summaries
- `--tool-results` — include (truncated) tool results
- `--thinking` — include assistant thinking blocks (only renders blocks whose plaintext was retained; signed-but-empty thinking shows nothing)
- `--sidechains` — include subagent conversations from each session's `subagents/`
- `--full` — shortcut for `--tools --tool-results --thinking --sidechains`
- `--max-chars N` — truncation limit for tool results / thinking (default 400)
- `--verbatim` — keep `<system-reminder>` and `<command-*>` tags instead of stripping
- `--raw` — plain text output, no markdown headers
- `--models` — annotate each assistant turn's badge with the model that produced it (reveals mid-session model switches and cross-session model differences)

Badges are assigned by argument order: the first session is `A·`, the second `B·`, and so on.

## Step 2: Handle ambiguity and errors

Resolution is per-argument and uses the same logic as `/replay`:

- **Ambiguous match**: if the merger exits with "matches multiple sessions", show the candidates and ask the user which path to use for that slot.
- **No match**: if it exits with "no session matching", tell the user and suggest `ls ~/.claude/projects/*/`.
- **Only one session given**: the merger errors with a reminder to use `/replay` instead.
- Sessions may live under different `cwd`s / projects — that's fine; the header lists each `cwd` it saw.

## Step 3: Present the output

- If the merged output is short (a few hundred lines), show it inline AND save it to `docs/replay-merge-<shortA>-<shortB>.md`.
- If it's large, save it to `docs/replay-merge-<shortA>-<shortB>.md` and show a brief summary plus the file path. Call out the interleaving pattern (who led, where the relay began, the division of labor) — that's the value a merged view adds over separate replays. Offer to surface specific turns.

## Notes

- Read-only: never modifies the original transcripts. It imports `extract-session.py` as a sibling module, so rendering and resolution stay in lock-step with `/replay`.
- For tandem sessions where the user copied responses between agents, `--verbatim` exposes the `/copy` and local-command wrappers that were the actual relay mechanism.
- `--models` is especially useful when API capacity issues or manual restarts caused a session to switch models partway through — the badge makes the boundary obvious.
