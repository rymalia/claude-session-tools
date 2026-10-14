---
session_id: 9124840b-11da-44c4-b28a-222f6538773b
date: 2026-10-14
time: "2026-10-13 3:49 PM PDT – 2026-10-14 12:17 AM PDT"
project: Peekaboo
---

# Session Summary: Peekaboo v4.9.2 skill migration, tool re-assessment, arc-cua comparison

## Overview

Migrated the local Peekaboo agent skill from a forked 3.6 copy to upstream's v4.9.2 skill plus a small, live-verified local overlay. The skill now lives in `claude-session-tools` and is symlinked into both Claude Code and Codex. Along the way the session reset the Peekaboo checkout to a clean upstream tracker, re-tested all 32 claims from the old skill, benchmarked Peekaboo against native tools, compared it with the arc-cua MCP, and updated the global agent instructions to match.

## Key Decisions Made

| Decision | Rationale |
|----------|-----------|
| **Skill = upstream SKILL.md unmodified + `## Local overlay`** | The 3.x skill was a fork of upstream's text, so each release silently made parts of it stale. Keeping upstream verbatim makes a refresh a replace plus a smoke test instead of a three-way merge; upstream's `docs/agent-skill.md` recommends this split. |
| **Skill home = `~/projects/claude-session-tools/skills/peekaboo`, symlinked into `~/.claude/skills` and `~/.codex/skills`** | User chose "option 1" (a small personal skills repo). One `git pull` updates both agents on both Macs, with no drift between copies. |
| **Reset Peekaboo `main` to `upstream/main`; archive old commits on `local/skills-3.6`** | User chose "reset to upstream (Recommended)". `main` becomes a clean tracker for `merge --ff-only`; the 4 local commits (old skill files and earlier summaries) are kept on the archive branch. |
| **Push URL for `upstream` set to `DISABLED-no-push-to-maintainer`** | Enforces the global fork-only rule mechanically. |
| **Claude MCP repointed from `npx` to `/opt/homebrew/bin/peekaboo mcp`** | Keeps the MCP server and CLI on the same binary and version (the npx server had been serving 4.9.2 while brew was 4.5.0). |
| **Recommend `screencapture -l` for known-window evidence; Peekaboo for finding windows and act loops** | Measured: `screencapture` 0.30s at 2× vs Peekaboo `see` 1.85s at 1×. Peekaboo's overhead buys stale-target refusal, which a plain screenshot doesn't need. |
| **arc-cua: bulk, low-stakes native AX only; MCP driver only, never `arc-cua run`** | About 20× faster per observe, but weaker stale-target checks, a menu-breaking side effect (finding C), open issues #5–#7, and the `run` loop sends screen state to cloud models. |
| **Pin arc-cua to 0.1.1 in the Codex config** | Unpinned `uvx --from arc-cua[macos]` picks up each new release on startup; pinned until the known issues are fixed. |
| **Did not run Codex review on the final instruction-file prose** | The text was built from claims already verified by hand against the source; stated to the user. |

## Changes Made

| Change | Detail |
|--------|--------|
| **Peekaboo repo** | Committed the two untracked summaries (`07f5e4051`). Created archive branch `local/skills-3.6`. Reset `main --hard` to `upstream/main` (`5f297f1bf`, v4.9.2+2). `main` has no tracking branch; `upstream` push URL disabled. |
| **New skill** | `claude-session-tools/skills/peekaboo/SKILL.md`: upstream v4.9.2 text plus overlay (privacy policy, tool-choice table, install parity, ~16 verified v4 traps, executable smoke test). Commit `ddffa06` (user pushed it this session). |
| **Evidence docs** | `claude-session-tools/docs/peekaboo-reverification-2026-10-13/`: README plus `01`–`04` evidence files (in `ddffa06`); an arc-cua vs Peekaboo section appended in `06e6e73` (not yet pushed). |
| **Skill installs** | `~/.claude/skills/peekaboo` and `~/.codex/skills/peekaboo` are symlinks to the repo folder; old installs backed up to `~/.peekaboo-skill-backup-2026-10-13/`. |
| **Claude MCP** | `claude mcp remove peekaboo -s user`, then `claude mcp add -s user peekaboo -- /opt/homebrew/bin/peekaboo mcp` (connected). |
| **`~/.claude/CLAUDE.md`** | Screenshots section: Peekaboo bullets now cover finding windows, act loops and the overlay; `screencapture -x -o -l <window_id>` for known-window evidence; new arc-cua paragraph; "with either tool" → "with any tool". |
| **`~/.codex/AGENTS.md`** | Same Peekaboo bullets and arc-cua paragraph, wrapped to that file's ~80-column style. |
| **`~/.codex/config.toml`** | arc-cua args pinned to `arc-cua[macos]==0.1.1`; backup at `~/.peekaboo-skill-backup-2026-10-13/codex-config.toml.before-arc-pin`. |

## Testing / Research Performed

- **32-claim re-test of the 3.6 skill on 4.9.2** (live, M3 MacBook Air, daemon host, all grants). Results are in `02-live-verdicts-4.9.2.md`. Codex gpt-5.6-luna independently produced source-based verdicts (`03-…`); disagreements were re-checked live.
- **Migration hints** for the removed commands (`list`, `image`, `inspect-ui`, `perform-action`, `hotkey`, `open`, `swipe`, `run`, `sleep`) and `--coords` confirmed live.
- **Benchmarks (Calculator window):**
  - `screencapture -x -o -l` 0.30s vs `peekaboo see --no-elements` 1.85s.
  - 5 background presses: JXA `AXPress` 3.56s vs Peekaboo `see`+`click` 5.78s.
  - Observe, warm: arc-cua `Driver.observe` 16–19 ms (1.24s cold, 35 elements) vs `peekaboo see --tree --no-screenshot --json` 0.34s (1.60s cold, 37 elements, 16.8 KB).
  - In each run the frontmost app stayed unchanged.
- **Codex luna passes:**
  - Source verdicts on the 32 claims.
  - Alternatives report.
  - Draft review: FIX, no Critical findings.
  - Review of the fixes.
  - arc-cua vs Peekaboo source comparison.
  - Of its skill-review findings, 9 were accepted and 2 rejected with live evidence.
  - For the arc comparison, three key claims were verified by hand against the source:
    - `run_command` acts on the key window (`mcp_server.py:196`).
    - Raw input without a snapshot gets no freshness check (`driver.py:504`).
    - The OpenAI Decisions payload includes base64 screenshots (`origin/master:policies/openai_decisions.py`).
- **Smoke test:** the overlay's smoke test passed verbatim (1+2=3 in a background Calculator, `SNAPSHOT_STALE` on snapshot reuse), plus a fail-fast negative control.
- **Validation:** `config.toml` parses with `tomllib` after the pin, and the pinned `uvx --from arc-cua[macos]==0.1.1 arc-cua --help` runs.
- **arc-cua status check:** PyPI still 0.1.1; issues #1, #4–#7 all open; 4 new upstream commits (`65e44f7..6b35303`), all in the decision loop or the Chrome backend, none in the driver/MCP.

## Discoveries / Handoff Notes

- **Removed in v4:** the commands `list`, `image`, `inspect-ui`, `perform-action`, `hotkey`, `open`, `swipe`, `run`, `sleep`. Flags renamed: `--coords` → `--at`, `--timeout-seconds` → `--timeout`.
- **Reversed in v4:**
  - Reusing a snapshot after a mutation returns `SNAPSHOT_STALE`.
  - A background `action AXPress` is refused without `--foreground`; use `click` for background presses.
- **v4 traps:**
  - `space list` needs `--no-remote` on the remote host.
  - Two daemon sockets can coexist (`daemon.sock` and `daemon-<hash>.sock`).
  - The MCP catalog is policy-filtered: 26 tools, `move` removed.
  - Calculator's AX display `value` can be empty, so check the result with a screenshot.
- **Homebrew:** the old `steipete/tap` is stuck at 4.5.0; the current formula is `openclaw/tap/peekaboo`.
- **arc-cua's 2026-10-06 assessment** quotes Peekaboo at 4–10s per observe. That was measured on 4.5.0 and is now historical (4.9.2 is 0.34s warm).
- **arc-cua's Chrome backend** drives its own CDP Chrome with a temporary profile, not the user's logged-in session.
- **arc-cua TCC:** its grants belong to whatever process runs `uvx` (the agent's terminal). Peekaboo's belong to its daemon or Peekaboo.app.
- **Codex invocation:** a `codex exec -C ~/projects` run exited 1 immediately (that directory isn't a git repo); re-running from inside a repo worked.
- **Stale Codex approval:** the `list` tool approval in `~/.codex/config.toml` no longer matches any v4 tool. It is harmless and was left in place.

## Current State

- Peekaboo `main` = `upstream/main` (`5f297f1bf`), clean apart from this summary (untracked). Submodules are not initialized (only builds need them).
- `claude-session-tools` `main` is ahead of origin by 1 (`06e6e73`). Pre-existing untracked docs there (e.g. `docs/codex-exec-plugin-injection.md`) were not touched.
- Brew CLI and Peekaboo.app are both 4.9.2. Calculator, used for the tests, was quit.
- Older Claude sessions may still run `npx` Peekaboo MCP processes until they restart.

## Summary Statistics

- 32 skill claims re-tested (about 7 still true, 11 changed, 6 obsolete, 2 reversed; 4 not run live, 3 of them kept as source-only items).
- 5 Codex luna passes.
- 4 benchmark comparisons.
- 3 commits: `07f5e4051` (Peekaboo archive branch), `ddffa06` and `06e6e73` (claude-session-tools).
- 3 global config files edited: `CLAUDE.md`, `AGENTS.md`, `config.toml`.
- 2 skill installs converted to symlinks.

### Unfinished Work

1. **Push** `06e6e73`: `cd ~/projects/claude-session-tools && git push -u origin main`.
2. **M4 MacBook setup:**
   - `brew install openclaw/tap/peekaboo` plus the matching Peekaboo.app.
   - Pull `claude-session-tools`.
   - Back up any existing installs, then `ln -s` the skill into `~/.claude/skills/peekaboo` and `~/.codex/skills/peekaboo`.
   - `claude mcp add -s user peekaboo -- /opt/homebrew/bin/peekaboo mcp` and the Codex MCP entry.
   - Grant permissions, then run the overlay smoke test.
   - Mirror the CLAUDE.md, AGENTS.md and arc-cua pin edits if those files aren't synced.
3. **Optional cleanup:**
   - Remove the stale `list` approval from `~/.codex/config.toml`.
   - `brew untap steipete/tap`.
   - Restart old Claude sessions so they drop the `npx` MCP servers.
4. **Untested items:** browser bridge (C11), the `app quit` collision (C16, unsafe to run live), `capture action` timing (C24), paste (C30), Chrome tab clicking.
5. **arc-cua:** revisit the 0.1.1 pin when upstream fixes #5–#7.
