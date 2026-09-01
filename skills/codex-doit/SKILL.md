---
name: codex-doit
description: >-
  Route work to the local Codex CLI as an independent second agent — self-contained,
  zero plugin dependency. Four modes: validate a PLAN before any code is written,
  review a DIFF after coding, get a quick SECOND OPINION on a snippet/question, or
  delegate a bounded IMPLEMENTATION (only when the user explicitly asks Codex to write
  code). Use on "codex doit", "route to codex", "ask codex", "have codex
  review/validate/check this", "codex second opinion", "get codex to look at this",
  "delegate this to codex", or any request to run Claude + Codex together as a
  review/delegation loop. By default Codex uses its own configured default model; the
  user may name a model (and optional reasoning effort) when summoning, e.g. "codex
  doit with gpt-5.6-terra xhigh". Do NOT use for trivial one-liners, prototypes, or
  throwaway scripts where the review ceremony costs more than the bug it would catch.

---

# codex-doit — route work to Codex, self-contained

Drive the local **Codex CLI** as an independent second agent (a *different* frontier
model) for review and delegation. **Claude conducts; Codex is a subordinate
reviewer/implementer called only through `codex exec`.** This skill is deliberately
**plugin-free** — it shells out to the `codex` binary directly and never depends on
the official `codex:` plugin being installed. (If that plugin is present you may use
it, but nothing here requires it.) Plugin-free cuts both ways: every `codex exec`
call here passes `--disable plugins`, so the Codex subagent itself runs without
plugin context too (see #12).

## The one idea

Use a second, independent model to critique your **plan before code** and your
**diff after code**, over a **git-based handoff** — not pasted transcripts. The win
isn't Codex specifically; it's the independent second opinion at the two cheapest
moments to catch a mistake.

## When to use / not use

✅ Complex/multi-step features · security- or perf-sensitive code · subtle bugs ·
large refactors · "measure twice, cut once" moments · any time you want an
adversarial second read before calling something done.

❌ One-line fixes · prototypes · scratch scripts · anything where the ceremony costs
more than the bug. Don't reach for Codex reflexively on trivial edits.

## Prerequisites (check once)

```bash
command -v codex && codex --version    # must resolve; verified against codex-cli 0.142.x
```

If missing/unauthenticated, tell the user and stop — do **not** improvise an auth
flow. Codex needs a git repo (or `--skip-git-repo-check`, but **ask the user first**
before adding that flag).

## The four modes

Classify the task, then use the matching invocation. Full copy-paste packets are in
`references/prompt-templates.md`; the shapes:

| Mode | When | Sandbox | Command core |
|------|------|---------|--------------|
| **1. Validate a plan** | before writing code | `-s read-only` | `codex exec --disable plugins -s read-only -c model_reasoning_effort=high "<plan packet>" < /dev/null` |
| **2. Review a diff** | after writing code | `-s read-only` | `codex exec --disable plugins -s read-only "<review packet>" < /dev/null` |
| **3. Second opinion** | a question / snippet | `-s read-only` | `codex exec --disable plugins -s read-only "<question packet>" < /dev/null` |
| **4. Delegate impl** | *only when the user explicitly asks Codex to write code* | `-s workspace-write` | `codex exec --disable plugins -s workspace-write "<task packet>" < /dev/null` |

If the user named a model when summoning the skill, insert the override right after
`codex exec` in any of these (see #4 below): `-m <model>` plus, if they gave an
effort token, `-c model_reasoning_effort=<effort>`.

Modes 1–3 are read-only (safe, backgroundable). Mode 4 writes — see the guardrail.

### Worked example (mode 2, end to end)

> **User:** "I just finished the retry-backoff change — have codex review it before I commit."

1. **Classify** → after code, a diff to critique → **Mode 2**.
2. **Fire it** (read-only, background, `< /dev/null`), pointing Codex at the diff via
   **git, not paste** — it reads `git diff` + the touched files itself. Use the mode-2
   packet from `references/prompt-templates.md`, filling in the *intent* + *scope*:
   ```bash
   codex exec --disable plugins -s read-only -c model_reasoning_effort=high "$(cat <<'EOF'
   <role>You are reviewing an implementation against its intent.</role>
   <task>Review the working-tree diff (`git diff`) + touched files.
   ## Intent
   Retry transient failures with capped exponential backoff.
   ## Scope
   Everything in the diff.</task>
   <output_contract>Findings by severity, file:line, mark inference vs fact,
   no style nits. End with SHIP or FIX.</output_contract>
   EOF
   )" < /dev/null      # Bash run_in_background: true
   ```
3. **On completion:** `grep`/`sed` the verdict + severity markers out of the log (don't
   Read the whole thing). If it claims a test is failing, **re-run the suite yourself** —
   its read-only run can't write temp dirs and false-fails (#10).
4. **Present** the findings to the user, severity-ordered, faithfully — then **STOP and
   ask which to fix**. Never auto-apply, even the obvious ones.

## Operational non-negotiables (the gotchas that actually bite)

1. **Always append `< /dev/null`** to every `codex exec` call. Claude Code's shell
   gives a non-TTY stdin that the CLI blocks on (`Reading additional input from
   stdin…` → hangs forever). This is the #1 failure. (Verified, codex-cli 0.139–0.142.)
2. **`-s read-only` for anything that isn't an explicit implementation delegation.**
   Read-only passes have no working-tree side effects.
3. **Run read-only passes in the background** — Bash `run_in_background: true`. They
   take minutes; you're notified on completion, then read the output and present. To
   wait, rely on that notification — **don't** chain a foreground `sleep` (Claude
   Code's harness blocks `sleep N && …`); if you must poll, background an
   `until ! pgrep -f 'codex exec'; do sleep 3; done`.
4. **Model: omit `-m` by default; honor a user-specified override.** With no model
   named, omit `-m`/`--model` entirely — the run inherits `~/.codex/config.toml`, so
   the skill never goes stale on model renames. But when the user names a model while
   summoning the skill (e.g. "codex doit with **gpt-5.6-terra xhigh**"), pass it
   through: the model name becomes `-m gpt-5.6-terra`, and a trailing effort token
   (`minimal|low|medium|high|xhigh`) becomes `-c model_reasoning_effort=xhigh`,
   overriding the per-mode effort defaults (#9). The override applies to every
   `codex exec` in that session of the skill, including `resume` calls. (Verified on
   codex-cli 0.144.x.)
5. **Wait for completion, then grep the verdict out of a big log.** A completed run
   *does* end with a final severity-ordered block + a `tokens used` trailer — but the
   reasoning/tool-call log above it can be 100–200 KB. Don't Read the whole file;
   `grep`/`sed` for the markers and verdict (`Critical|Major|SHIP|FIX|PROCEED|REVISE`).
   If you catch it "mid-investigation" with no verdict, you read the file **before the
   job finished** — wait for the completion notification first (see #3).
6. **Banned flags:** `--full-auto` (removed ≥0.139) and `-a on-failure` (deprecated)
   will error. If genuine autonomy is needed, that's a mode-4 delegation, not a review.
7. **Reviews never auto-apply.** Present findings, then STOP and ask which to fix.
   Auto-applying is forbidden even when the fix looks obvious.
8. **Verify Codex's claims yourself.** It's a reviewer, not an oracle. Reproduce a
   claimed bug before trusting it; present its output faithfully (keep severity,
   file:line, and its inference-vs-fact distinctions).
9. **Bump reasoning for hard critique:** `-c model_reasoning_effort=high` for
   plan/security/architecture passes. Default effort is fine for quick opinions.
10. **Distrust Codex's own test/build counts.** Under `-s read-only` it can't write
    temp dirs, so a suite it runs itself spuriously fails (`mkdtemp EPERM`) and
    mis-reports — e.g. it says "82/1" where the 1 is the sandbox, not a bug. **Re-run
    the suite yourself; your local number is truth.** This is the gotcha most likely to
    cause a *wrong decision* (shipping on a false red, or chasing a phantom failure).
    Letting Codex genuinely run tests requires a mode-4 `workspace-write` delegation.
11. **Frame security reviews defensively, or they get refused outright.** OpenAI's cyber
    filter kills adversarially-worded prompts: "offensive security reviewer… find
    bypasses… exploit" returned `This content was flagged for possible cybersecurity
    risk… Trusted Access for Cyber program` — **73K tokens, zero findings**. The same
    technical scope, reframed as "senior engineer reviewing a defensive allowlist for
    completeness… report permitted commands that would modify the filesystem", ran clean
    and produced **9 findings with a FIX verdict**. Only the framing changed. Write the
    prompt from the defender's seat: you own the control, you want it complete, and
    findings are gaps in *your* coverage — never an attack you are mounting. Ask for
    "permitted commands that would <do the bad thing>", not "bypasses". This also gets
    *better* output, because completeness-of-coverage is a more tractable question than
    open-ended exploitation. (Verified 2026-07-27, codex-cli 0.144.x, gpt-5.6-terra.)
12. **Always pass `--disable plugins`** on every `codex exec` call, including
    `resume` (options go before the subcommand). Without it, Codex injects a
    `<recommended_plugins>` catalog — plus any installed plugins' skills, connectors,
    and MCP tools — into the subagent's context: pure token pollution for a
    review/delegation run. This is the **only verified gate**: `--disable
    recommended_plugins` alone does NOT suppress the catalog, `--disable-plugins`
    (hyphenated) is an unknown-flag error, and env vars like `CODEX_NON_INTERACTIVE`
    don't touch it. Core shell/file tools are unaffected — only plugin-provided
    capabilities go away; in the rare mode-4 delegation that genuinely needs a plugin
    tool, drop the flag for that one call and tell the user. Keep it per-invocation:
    never `codex features disable plugins`, which would persist to
    `~/.codex/config.toml` and strip the user's interactive sessions too. Two
    verified fine points: a short built-in `### Available skills` list (imagegen,
    openai-docs, plugin-creator) still appears — those are Codex-bundled skills, not
    plugins, so a context probe will still "see skills"; and plugin-provided
    lifecycle hooks (SessionStart/UserPromptSubmit/Stop) stop firing under the flag.
    In one A/B probe the flag cut the run from 20.5K to 9.1K tokens. (Verified
    codex-cli 0.147.0, live A/B test 2026-08-07.)

## The handoff contract (how state crosses the boundary)

The two agents share **no** conversation memory. Context crosses as **git state + an
explicit task packet**, never pasted transcripts. Every handoff carries:

```
Task:        one sentence — validate this plan | review this diff | answer this | implement this narrow change
Scope:       repo, branch, diff against base, the specific files X / Y / Z
Constraints: read-only | write-capable | no broad refactors | preserve public API
Ownership:   Claude edits | Codex may edit | read-only review only
Output:      findings first with file:line; separate observed facts from inference;
             if editing, list touched files + the verification command run
```

`Ownership` is what turns "don't edit concurrently" from advice into an enforceable
rule: exactly one agent owns writes to a given file at a time. Point Codex at files
and git; don't paste giant transcripts (it drifts context and wastes tokens).

## Write-capability guardrail (mode 4 only)

`codex exec -s workspace-write` **edits files**. When you delegate an implementation:

- Do it **only when the user explicitly asks Codex to implement** — never silently.
- It runs **non-interactively** (exec mode) — no approval prompt; writes are sandboxed
  to the workspace. You can background it, but hold your own edits meanwhile.
- **Stop editing the same files yourself.** Wait for the job to finish, inspect the
  resulting `git diff`, then decide keep / modify / revert. Never edit concurrently.
- Give it a tight scope + a verification command to run before finishing, and require
  it to report touched files + the verify result.

## Cost note

These passes aren't free (a thorough plan review runs ~50–150 K tokens). Worth it for
complex/risky work; skip it for one-liners. Scale the ceremony to the risk.

## Loop shape (review modes)

1. Write the plan (or make the change).
2. Fire the matching `codex exec` (read-only, background, `--disable plugins`,
   `< /dev/null`).
3. On completion: grep the output for findings, **summarize to the user**, ask whether
   to revise/fix or proceed. Don't silently act.
4. Apply agreed fixes; re-run if the change was material.

## References

- `references/prompt-templates.md` — copy-paste XML packets for all four modes, plus
  the session-continuity (`resume`) form.
