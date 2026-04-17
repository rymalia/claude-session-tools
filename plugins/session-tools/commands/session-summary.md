# /session-summary — Generate End-of-Session Summary

Generate a comprehensive session summary document with accurate timestamps and metadata.

## Step 1: Collect Metadata in One Call

Run this single command to gather the end-time and project metadata in one shot:

```bash
bash "$SESSION_TOOLS_ROOT/scripts/collect-metadata.sh"
```

Output is `key: value` lines. Parse:

- **now**: session end time. Always present.
- **project**: always present.
- **branch**: omitted if not in a git repo.
- **open_prs**: JSON array; omitted if `gh` is not installed.

**Do NOT invoke `/now` as a separate skill or slash command** — the `now:` line from this script replaces it. Invoking `/now` from inside `/session-summary` is fragile across Claude Code clients (skill-name resolution varies).

If `$SESSION_TOOLS_ROOT` is unset (e.g. a session that started before the plugin was updated), fall back to: (a) the cwd from your environment for the project name, (b) the git branch from the initial git status block, and (c) run `date '+%Y-%m-%d %I:%M %p %Z'` for the end time. Do not run separate `basename`/`git branch`/`gh pr list` commands to work around a missing `$SESSION_TOOLS_ROOT`; it defeats the purpose of the consolidation.

## Step 2: Gather Start and Resume Timestamps

**Start time**: Check if `SESSION_START_TIME` is visible in your current context (it is injected by the SessionStart hook). If not, retrieve it by running:

```bash
echo $SESSION_START_TIME
```

**Resume times**: Check if `SESSION_RESUME_TIME` is visible in your current context. If not, run:

```bash
echo $SESSION_RESUME_TIME
```

If the value is empty, the session was not resumed — omit the `resumed` field entirely.

## Step 3: Map Fields to Frontmatter

- **project**: from the `project:` line.
- **branch**: from the `branch:` line. Also omit the frontmatter `branch` field when the branch is `main`/`master` with no meaningful branch context.
- **related_pr**: from the `open_prs:` JSON array. If a PR was created or worked on during this session, include its number. Omit if not applicable. Do not include with an empty value.
- **time range**: start from `SESSION_START_TIME`, end from the script's `now:` line.

## Step 4: Write the Summary

Save to: `docs/session-summary-YYYY-MM-DD-{VERY SHORT DESCRIPTOR}.md`

Use today's date. The descriptor should be 2-4 lowercase words separated by hyphens summarizing the session's main focus.

**Scale depth to the session's complexity.** A quick bug fix needs a few paragraphs. A multi-phase session that restructures the dev environment needs detailed sections and narrative. Match the summary to the work.

### Frontmatter

Format the `time` field as a range using only the time portion and timezone, e.g. `"4:02 PM PDT – 6:30 PM PDT"`. If the start and end dates differ, include dates in the range.

```yaml
---
date: YYYY-MM-DD
time: "<start time> – <end time>"
resumed: "<resume1>, <resume2>, ..."
project: <project folder name>
branch: <branch name>
related_pr: <PR number>
---
```

Remember:
- `resumed`: omit entirely if session was not resumed
- `branch`: omit entirely if not applicable
- `related_pr`: omit entirely if not applicable

### Body — Required Sections

- **Overview**: 1-2 sentence summary of what was accomplished
- **Key Decisions Made**: Strategic choices and rationale
- **Changes Made**: Use a markdown table:

  | Change | Detail |
  |--------|--------|
  | **Short name** | What was done and where |

- **Testing / Research Performed**: Verification and validation steps taken. For research or planning sessions that have no code testing, use "Research Performed" and quantify investigation scope (files audited, features catalogued, external sources analyzed) — not just file changes.
- **Summary Statistics**: Lines changed, files modified, bugs fixed, etc. For research sessions, include investigation metrics (e.g. "11 source files audited", "6 undocumented features catalogued").
- **Unfinished Work**: Notes and next steps on things that didn't get finished

### Body — Optional Sections

Include these when the session warrants them:

- **Discoveries / Handoff Notes**: Root cause analyses, environment state, non-obvious gotchas, or lessons learned that a future session would otherwise have to re-discover. This is different from "Unfinished Work" — it's context and insight, not tasks. Examples: "CLAUDE.local.md overrides CLAUDE.md for runtime instructions", "the `--pull` flag is dead code", "LaunchAgent KeepAlive masks version problems."
- **Current State**: A snapshot of where things stand right now — running services, binary paths, branch topology, uncommitted files. Useful for handoff when the environment is complex.
- **Issues & PRs**: Dedicated section with links when the session involved filing issues or submitting/reviewing PRs. Include full URLs for easy navigation.
- Any other domain-specific sections the session warrants (e.g. "The Bug", "Root Cause Analysis", "How We Got Here"). Do not force content into prescribed sections when a custom section would communicate it better.

## Important

- Do NOT estimate or guess timestamps. Every timestamp must come from `SESSION_START_TIME`, `SESSION_RESUME_TIME`, or `/now`.
- Do NOT skip the metadata gathering steps. Run the commands even if you think you know the values.
- If `SESSION_START_TIME` is unavailable from both context and the environment variable, note this in the summary and leave the start time as `""` for the user to fill in.
