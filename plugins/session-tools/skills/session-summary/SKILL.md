---
name: session-summary
description: Generate and save a durable end-of-session summary with exact Codex session metadata, decisions, changes, verification, discoveries, current state, and unfinished work. Use when the user invokes $session-summary or asks to recap, summarize, close out, or preserve the valuable context from the current coding session.
---

# Session Summary

Create a factual handoff document while the current session context is still available.

## Workflow

1. Read [references/summary-contract.md](references/summary-contract.md) completely before writing the summary.

2. Collect end-time and project metadata in one call:

   - Resolve the plugin root as two directories above this `SKILL.md` file.
   - Run `bash "<plugin-root>/scripts/collect-metadata.sh"` exactly once.
   - Parse its `now`, `project`, optional `branch`, and optional `open_prs` lines.
   - Do not replace the consolidated call with separate date, project, branch, or PR commands.

3. Read the authoritative session metadata injected by the plugin's `SessionStart` hook. It is labeled `SESSION_SUMMARY_METADATA` and contains:

   - `session_id`
   - `start_time`
   - `resume_times`

   If the hook metadata is unavailable, use `CODEX_THREAD_ID` for `session_id` only when that environment variable is present. Never infer a start or resume timestamp. Leave the start blank as directed by the contract and explain why. Do not parse the Codex transcript to recover timestamps; its storage format is not part of this skill's contract.

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
