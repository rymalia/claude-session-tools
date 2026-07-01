# /replay-merge — Merge & Replay Multiple Sessions

Merge two or more prior Claude Code sessions into a single, timestamp-sorted replay. Every event from every named session is pooled and rendered in true chronological order, with each turn badged by its origin session — so sessions that ran in tandem (e.g. you relaying responses between two parallel agents) read as one coherent timeline.

Usage: `/replay-merge <id-or-path> <id-or-path> [<id-or-path> ...] [flags]`

Each positional argument is a session UUID, a prefix (≥4 chars), or an absolute path to a `.jsonl` file — resolved exactly like `/replay`. **At least two sessions are required**; for a single session use `/replay`.

## Step 1: Run the merger

This command **always saves its output to a file** — pass `--save-dir docs` so the merger writes the result and reports the path (the same always-save contract as `/replay`):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/merge-sessions.py" $ARGUMENTS --save-dir docs
```

By default the output is conversation-only (user turns + assistant text), harness noise stripped — same as `/replay`. The merge-specific behavior: turns from all sessions are interleaved by timestamp, and each header carries an origin badge like `A·495d4d49`.

Each positional session is auto-detected as a **Claude Code** transcript or an **OpenAI Codex** rollout, resolved exactly as `/replay` does — and **the two can be mixed in a single merge**. A Codex session and a Claude session interleave into one chronological timeline, each turn badged by origin; Codex sessions additionally show their CLI version in the header line. (Codex rollouts have no subagent sidechains, so `--sidechains` simply doesn't apply to them.)

Flags (mirror `/replay`, plus `--models`):

- `--tools` — include one-line tool-call summaries
- `--tool-results` — include (truncated) tool results
- `--thinking` — include assistant thinking blocks (only renders blocks whose plaintext was retained; signed-but-empty thinking shows nothing)
- `--sidechains` — include subagent conversations from each session's `subagents/`
- `--full` — shortcut for `--tools --tool-results --thinking --sidechains`
- `--max-chars N` — truncation limit for tool results / thinking (default 400)
- `--verbatim` — keep `<system-reminder>` and `<command-*>` tags instead of stripping
- `--raw` — plain text output, no markdown headers
- `--embed-images` — embed images inline as base64 `data:` URIs so they render in the markdown (default is a lean `[Image #N: <media_type>]` placeholder); ignored in `--raw`
- `--save-dir DIR` — write to a flag-derived, non-clobbering file in `DIR` (created if missing) and print the saved path instead of dumping to stdout
- `--models` — annotate each assistant turn's badge with the model that produced it (reveals mid-session model switches and cross-session model differences)

Badges are assigned by argument order: the first session is `A·`, the second `B·`, and so on.

### Output filename

With `--save-dir`, the merger names the file `replay-merge-<shortA>-<shortB>[…][-<flags>].md` — every session's 8-char short id, then the view flags in the same canonical order `/replay` uses (so flag order on the command line doesn't change the name). Existing files are never overwritten; collisions get `-2`, `-3`, …. Do not construct the filename yourself.

## Step 2: Handle ambiguity and errors

Resolution is per-argument and uses the same logic as `/replay`:

- **Ambiguous match**: if the merger exits with "matches multiple sessions", show the candidates and ask the user which path to use for that slot.
- **No match**: if it exits with "no session matching", tell the user and suggest `ls ~/.claude/projects/*/`.
- **Only one session given**: the merger errors with a reminder to use `/replay` instead.
- Sessions may live under different `cwd`s / projects — that's fine; the header lists each `cwd` it saw.

## Step 3: Present the output

The merger has already written the file (Step 1) and printed a `saved: <path> (N turns, M lines)` line. Always report that path. The merge is deterministic Python; the only frontier-model cost is reading the file back to summarize it — and merges pool several sessions, so that file is usually *larger* than a single replay. Route the read by size and intent:

- **File only (no summary asked).** Report the `saved:` path; don't read it back.
- **Short merge (a few hundred lines).** `Read` the saved file and show it inline. No subagent.
- **Large merge + summary wanted.** Do **not** `Read` the raw file into this context. Delegate the bulk read to a **Sonnet subagent** (`Agent` tool, `subagent_type: general-purpose`, `model: sonnet`): have it Read the merged file and return a compact digest that foregrounds the interleaving pattern — who led, where the relay began, the division of labor. Comment on that digest, keeping the full merged transcript out of this context. The interleaving story is the value a merged view adds over separate replays, so brief the subagent to surface it explicitly. Offer to surface specific turns.

## Notes

- Read-only: never modifies the original transcripts. It imports `extract-session.py` as a sibling module, so rendering and resolution stay in lock-step with `/replay`.
- For tandem sessions where the user copied responses between agents, `--verbatim` exposes the `/copy` and local-command wrappers that were the actual relay mechanism.
- `--models` is especially useful when API capacity issues or manual restarts caused a session to switch models partway through — the badge makes the boundary obvious.
