---
name: session-summary
description: Generate and save a durable end-of-session summary with exact session metadata, decisions, changes, verification, discoveries, current state, and unfinished work. Works in both Claude Code (/session-tools:session-summary, or /session-summary when the bare name is unclaimed) and OpenAI Codex ($session-tools:session-summary). Use when the user invokes the command or asks to recap, summarize, close out, or preserve the valuable context from the current coding session.
allowed-tools:
  - Bash(${CLAUDE_SKILL_DIR}/scripts/collect-metadata.sh)
---

# Session Summary

Create a factual handoff document while the current session context is still available. One skill serves both hosts; the few steps that differ are labelled **Claude Code** or **Codex**.

**Which host am I on?** If a `SESSION_SUMMARY_METADATA` block is present in your context, you are on **Codex** — the `${CLAUDE_*}` variables below will also appear as literal, unsubstituted text. Otherwise you are on **Claude Code**, which has already substituted those variables with real values.

## Workflow

1. Read [references/summary-contract.md](references/summary-contract.md) completely before writing the summary.

2. **Collect metadata in one call.** Run the bundled collector exactly once — never substitute separate `date`, `basename`, `git`, or `gh` calls:

   - **Claude Code:** run `${CLAUDE_SKILL_DIR}/scripts/collect-metadata.sh` directly (it is executable — do not prefix with `bash`). This skill's `allowed-tools` pre-authorizes that exact path, so it runs without a permission prompt and needs no user allowlist entry.
   - **Codex:** run the `scripts/collect-metadata.sh` file in this skill's own directory (the directory containing this `SKILL.md`); use its absolute path.

   Parse its lines: `now` and `project` (always), optional `branch`, optional `open_prs`, and — on Claude Code — `session_start` and `session_resume`. **If the collector fails or emits nothing, stop and report the failure to the user; do not synthesize or estimate any metadata.**

3. **Read the session id and timestamps** for the host you detected above. Never estimate a timestamp; leave a missing start time blank per the contract and explain why in the body.

   - **Claude Code:**
     - `session_id`: `${CLAUDE_SESSION_ID}` — Claude Code substitutes the real id here.
     - Start and resume times: use the collector's `session_start` and `session_resume` lines. (These come from the SessionStart hook and equal the `SESSION_START_TIME` / `SESSION_RESUME_TIME` values already in your context.)
   - **Codex:** take `session_id`, `start_time`, and `resume_times` from the `SESSION_SUMMARY_METADATA` block. If that block is absent, use `CODEX_THREAD_ID` for `session_id` only when it is present, and leave the start time blank. Do not parse the Codex transcript to recover timestamps; its storage format is not part of this skill's contract.

4. Reconstruct the session from the conversation and observed tool results. Capture:

   - what was accomplished;
   - decisions and their rationale;
   - files or systems changed;
   - tests and research actually performed;
   - discoveries a future session would otherwise need to rediscover;
   - current state and unfinished work.

   Inspect the workspace only when needed to verify a claim. Respect repository instructions and do not attribute pre-existing worktree changes to this session. Never claim a command ran or a result passed unless the session contains evidence.

5. Write the summary under `docs/` using the filename and structure in the contract. Check whether the target path already exists before writing. Never overwrite an existing summary; choose a more specific descriptor if necessary.

6. Re-read the saved file and verify:

   - every timestamp came from hook or metadata-script output;
   - optional frontmatter fields with no value were omitted;
   - decisions include rationale;
   - testing and research claims are evidence-backed;
   - unfinished work is explicit, even when there is none.

Report the saved path to the user.
