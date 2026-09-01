git add skills/codex-doit/SKILL.md \
        skills/codex-doit/references/prompt-templates.md \
        skills/codex-doit/eval/trigger-eval.py

Commit message:

Add codex-doit skill: route work to the local Codex CLI

Self-contained, plugin-free skill for using the local `codex` CLI as an
independent second agent. Shells out to `codex exec` directly — no dependency
on the official codex: plugin.

Four modes, classified by task: validate a PLAN before code, review a DIFF
after code, quick SECOND OPINION on a snippet/question, or delegate a bounded
IMPLEMENTATION (write-capable, only when the user explicitly asks Codex to
code). Copy-paste XML prompt packets for each in references/prompt-templates.md,
plus the verified `resume`/`--last` session-continuity form.

Bakes in the operational non-negotiables learned in practice:
- always append `< /dev/null` (non-TTY stdin otherwise hangs forever)
- read-only sandbox by default; background read-only passes
- never pass -m (inherit ~/.codex/config.toml so it can't go stale)
- distrust Codex's own test/build counts — a read-only run can't write temp
  dirs and false-fails (mkdtemp EPERM); re-run the suite locally
- reviews never auto-apply; verify claims; present findings faithfully
- mode-4 ownership lock: one writer per file, wait-inspect-diff-reconcile

Validated before commit:
- Behavior: 5/5 blind context-free runs (one per mode + a decline case).
- Triggering: fires Skill(codex-doit) reliably on core phrasings with no sibling
  collision vs the codex / codex-plan-review skills (verified via real claude -p).

Includes references/prompt-templates.md (task-packet shapes) and
eval/trigger-eval.py (regression harness for the description).
