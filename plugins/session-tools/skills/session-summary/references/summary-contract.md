# Session Summary Contract

## Output path

Save to:

```text
docs/session-summaries/session-summary-YYYY-MM-DD-{very-short-descriptor}.md
```

Create `docs/session-summaries/` if it does not exist. This path applies unconditionally in every project; older summaries sitting at `docs/` root are fine to leave where they are.

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

### Close-out section

Every summary ends with exactly one close-out section. Which one depends on whether the repository declares a session-close contract (see below):

- **No contract declared (default):** `### Unfinished Work` — state remaining tasks and next steps. Write `None.` when the session genuinely finished everything rather than omitting the section.
- **Contract declared:** the contract's `closing_section`, in its `closing_format`, and **no** `Unfinished Work` section. The repository's tracker is the only backlog; the summary reports what the session changed in it and adds no work.

## Optional body sections

Include these when they improve the handoff:

- **Discoveries / Handoff Notes**: root causes, non-obvious behavior, environment facts, and lessons a future session would otherwise rediscover.
- **Current State**: running services, active paths, branch topology, uncommitted files, or other relevant environment state.
- **Issues & PRs**: links to issues or PRs filed, reviewed, or changed during the session. Include full URLs.
- Domain-specific sections such as **The Bug**, **Root Cause Analysis**, or **How We Got Here** when the prescribed sections would obscure the story.

Keep discoveries separate from unfinished work: discoveries are context; unfinished work is action.

## Repository session-close contract

A repository may own its own definition of "what a session leaves behind" — typically because it runs a tracker whose versioned items are the single backlog, so a prose "unfinished work" list would be a second, drifting authority. It declares that by committing:

```text
docs/session-summaries/session-close-contract.yml
```

Check for this file before writing (step 1 of the workflow). If the file exists but cannot be parsed, lacks a required key, or declares a `version` other than `1`, **fail closed**: stop, report the problem to the user, and do not write a summary under either rule set — the default close-out applies only when the file is absent. If it is absent, the default rules above apply unchanged. If it is present, obey it exactly:

```yaml
version: 1
closing_section: "Board updated"          # required — replaces "Unfinished Work"; must be the LAST section
closing_format: "- WI-NNN: <state>"       # required — the only body the closing section may have
forbidden_sections:                       # required — headings that must not appear anywhere
  - "Unfinished Work"
  - "Next Steps"
check_command: "npm run pm -- summary-check {file}"   # optional — run after saving; `{file}` = summary path
```

Rules when a contract is declared:

1. The final section of the summary is `## <closing_section>` and nothing follows it.
2. Its body follows `closing_format` literally: one line per tracker item whose state the session changed, using the repository's real ids and states. If nothing changed, write the contract's stated empty form (for example `- none`). Do not paraphrase, do not add prose.
3. None of the `forbidden_sections` headings may appear at any level, and no other section may carry a next-work list, priority order, or copied backlog. "What's next" lives in the tracker; the summary may say *where* the tracker is, never *what it contains*.
4. `Current State` and `Discoveries / Handoff Notes` remain allowed — they are context, not action items.
5. If `check_command` is present, run it with `{file}` replaced by the saved path after writing the summary, and fix what it reports before reporting the path to the user. It is a validator only; it never changes tracker state, and a failure is not a reason to fall back to the default close-out.
6. The contract file is read-only from the skill's point of view. Never create, edit, or remove it as part of writing a summary.

Worked examples live in [examples/](examples/): the default close-out, a contract-conforming close-out, and an annotated set of contract violations.

## Accuracy rules

- Never estimate or guess timestamps.
- Never skip the consolidated metadata call.
- Never claim tests, research, edits, commits, pushes, issues, or PRs without session evidence.
- Distinguish changes made during this session from unrelated pre-existing workspace state.
- Prefer a useful narrative over mechanically filling sections with repetitive content.
- Copy counts, ids, and states from evidence in the session, and re-read each one against its source before saving; a swapped pair of numbers is a false claim.
