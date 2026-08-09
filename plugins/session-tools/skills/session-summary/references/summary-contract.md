# Session Summary Contract

## Output path

Save to:

```text
docs/session-summary-YYYY-MM-DD-{very-short-descriptor}.md
```

Use the end date from the metadata script. Make the descriptor two to four lowercase words separated by hyphens and representative of the session's main focus.

Scale depth to the session's complexity. A quick fix needs a few paragraphs; a multi-phase investigation or environment restructuring warrants detailed sections and narrative.

## Frontmatter

Use:

```yaml
---
session_id: <session id>
date: YYYY-MM-DD
time: "<start time> – <end time>"
resumed: "<resume1>, <resume2>, ..."
project: <project folder name>
branch: <branch name>
related_pr: <PR number>
---
```

Apply these rules:

- Use only the time portion and timezone when start and end occurred on the same date, for example `"4:02 PM PDT – 6:30 PM PDT"`.
- Include dates in the range when start and end occurred on different dates.
- If the start time is unavailable, leave the start as `""` for the user to fill in and explain the missing hook metadata in the body. Do not estimate it.
- Omit `session_id` when unavailable.
- Omit `resumed` when the session was not resumed.
- Omit `branch` when outside a git repository or on `main`/`master` without meaningful branch context.
- Include `related_pr` only when a PR was created or worked on during this session. An open PR is a candidate, not proof of relevance.
- Never emit empty optional fields.

## Required body sections

### Overview

Summarize what was accomplished in one or two sentences.

### Key Decisions Made

Record strategic or implementation choices and their rationale. Use a table when there are multiple decisions:

| Decision | Rationale |
|----------|-----------|
| **Short decision** | Why this choice was made |

### Changes Made

Use:

| Change | Detail |
|--------|--------|
| **Short name** | What was done and where |

### Testing / Research Performed

List verification and validation actually performed. For a research or planning session with no code testing, title this section `Research Performed` and quantify the investigation scope, such as files audited, behaviors catalogued, or external sources analyzed.

### Summary Statistics

Include useful, defensible metrics such as files modified, checks run, bugs fixed, source files audited, or features catalogued. Do not manufacture line counts or treat all current worktree changes as session changes.

### Unfinished Work

State remaining tasks and next steps. Write `None.` when the session genuinely finished everything rather than omitting the section.

## Optional body sections

Include these when they improve the handoff:

- **Discoveries / Handoff Notes**: root causes, non-obvious behavior, environment facts, and lessons a future session would otherwise rediscover.
- **Current State**: running services, active paths, branch topology, uncommitted files, or other relevant environment state.
- **Issues & PRs**: links to issues or PRs filed, reviewed, or changed during the session. Include full URLs.
- Domain-specific sections such as **The Bug**, **Root Cause Analysis**, or **How We Got Here** when the prescribed sections would obscure the story.

Keep discoveries separate from unfinished work: discoveries are context; unfinished work is action.

## Accuracy rules

- Never estimate or guess timestamps.
- Never skip the consolidated metadata call.
- Never claim tests, research, edits, commits, pushes, issues, or PRs without session evidence.
- Distinguish changes made during this session from unrelated pre-existing workspace state.
- Prefer a useful narrative over mechanically filling sections with repetitive content.
