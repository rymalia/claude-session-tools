# codex-doit — prompt templates

Copy-paste-ready `codex exec` packets for each mode. Style: compact, XML-tagged, with
an explicit output contract — prompt Codex like an operator, not a collaborator.

## Conventions (read once)

- **Always append `< /dev/null`** — or `codex exec` hangs on the non-TTY stdin.
- **Always pass `--disable plugins`** — suppresses the `<recommended_plugins>`
  catalog injection and all plugin-provided skills/connectors/MCP tools in the
  subagent's context (core shell/file tools are unaffected). It's the only verified
  gate: `--disable recommended_plugins` alone does NOT suppress the catalog, and
  `--disable-plugins` (hyphenated) errors. Per-invocation only — never
  `codex features disable plugins`. (Verified codex-cli 0.147.0.)
- **Model: omit `-m` by default** — inherit `~/.codex/config.toml`. If the user named
  a model when summoning the skill (e.g. "gpt-5.6-terra xhigh"), insert
  `-m <model>` right after `codex exec` in any template below, plus
  `-c model_reasoning_effort=<effort>` if they gave an effort token
  (`minimal|low|medium|high|xhigh`) — that override replaces the per-mode effort
  guidance.
- **Sandbox:** `-s read-only` for modes 1–3; `-s workspace-write` only for mode 4.
- **Background** the read-only passes (Bash `run_in_background: true`).
- **Effort:** add `-c model_reasoning_effort=high` for plan / security / architecture
  critique. Skip for quick opinions.
- **Banned:** `--full-auto` (removed), `-a on-failure` (deprecated). Non-git dirs:
  `--skip-git-repo-check` only after asking the user.
- **Point at files + git; don't paste transcripts.** Codex runs inside the repo and can
  read files and the working-tree diff itself.
- **Distrust Codex's own `npm test`/build numbers** from a `-s read-only` pass — it
  can't write temp dirs, so it reports false failures (`mkdtemp EPERM`). Re-run the
  suite yourself; your local number is truth.

---

## Mode 1 — Validate a plan (before code)

```bash
codex exec --disable plugins -s read-only -c model_reasoning_effort=high "$(cat <<'EOF'
<role>
You are a senior engineer reviewing an implementation PLAN before any code is written.
Find the flaws now, while they are cheap to fix.
</role>

<task>
Review the plan below for correctness, completeness, and risk. Read repo files as needed.
PLAN:
---
<<PASTE .codex-loop/plan.md OR INLINE PLAN>>
---
</task>

<check>
- Logic gaps and unhandled edge cases
- Architecture / design flaws and simpler alternatives
- Security (authz, input validation, data exposure, injection)
- Missing requirements or hidden dependencies
- Step ordering / sequencing hazards
</check>

<output_contract>
List findings ordered by severity (Critical|Major|Minor|Info). For each: the plan step
it affects, the problem, and a concrete fix. Separate confirmed facts (from reading the
repo) from inference. If the plan is sound, say so and note only residual risks.
Do not restate the plan. End with a REVISE or PROCEED verdict.
</output_contract>
EOF
)" < /dev/null
```

### Security-focused variant
Swap `<check>` for authn/authz gaps · input-validation coverage · secrets/data exposure ·
injection vectors (SQL/command/XSS/path) · OWASP Top 10. Add: "Evidence-based only —
flag guesses as hypotheses. No style feedback."

---

## Mode 2 — Review a diff (after code)

Codex sees the working-tree diff itself; name the scope and intent so it knows what
"correct" means.

```bash
codex exec --disable plugins -s read-only "$(cat <<'EOF'
<role>You are reviewing an implementation against its intent.</role>

<task>
Review the current working-tree changes. Read the diff (`git diff`) and the touched files.
## Intent
<<ONE PARAGRAPH: what this change is supposed to do>>
## Scope
Files: <<A / B / C>>   (or: everything in the diff)
</task>

<check>
- Bugs, logic errors, regressions
- Deviations from the stated intent
- Performance (complexity, N+1, unbounded loops, I/O)
- Security vulnerabilities
</check>

<output_contract>
Findings ordered by severity (Critical|Major|Minor|Info), each with file:line and a
concrete fix. Mark inference vs confirmed. No style nits. End with SHIP or FIX.
</output_contract>
EOF
)" < /dev/null
```

For a skeptical "why shouldn't this ship" pass, change the role to an adversarial
reviewer whose default is FIX unless the change is provably safe.

> **Aside — the built-in `codex exec review`.** Codex ships a turnkey
> `codex exec review` subcommand that reviews the current repo with no prompt to write.
> Prefer the custom packet above: it lets you state *intent* and *scope* (so Codex knows
> what "correct" means) and pins a consistent `SHIP`/`FIX` verdict the loop can parse.
> Reach for the built-in only for a quick, throwaway ad-hoc review where writing a packet
> isn't worth it.

---

## Mode 3 — Second opinion (question or snippet)

```bash
codex exec --disable plugins -s read-only "$(cat <<'EOF'
<role>You are an independent second opinion from a different model.</role>
<task>
<<THE QUESTION, or paste the specific snippet/file to react to>>
</task>
<output_contract>
Give a direct answer. If it's code: correctness first, then one better alternative if a
clearly better one exists. Flag guesses as guesses; say what you'd need to be sure.
</output_contract>
EOF
)" < /dev/null
```

---

## Mode 4 — Delegate a bounded implementation (WRITE — only when the user asks)

`-s workspace-write` lets Codex edit files. Use **only** when the user explicitly asks
Codex to implement. Enforce the ownership lock: stop editing those files yourself, wait
for the result, inspect the diff, then reconcile.

```bash
codex exec --disable plugins -s workspace-write "$(cat <<'EOF'
<role>You implement a narrow, well-specified change and nothing more.</role>

<task>
<<PRECISE description of the change>>
</task>

<constraints>
- Scope strictly to: <<the files named>>. No broad refactors, no drive-by changes.
- Preserve the public API / existing behavior outside the change.
- Run <<VERIFY COMMAND, e.g. `npm test`>> before finishing; do not finish red.
</constraints>

<output_contract>
List the files you touched and the exact verification command you ran with its result.
If you could not complete it, say precisely where you stopped and why.
</output_contract>
EOF
)" < /dev/null
```

Then: read the result, run `git diff` / the verify command yourself, and present the
outcome. Do not commit — the user commits.

---

## Session continuity (resume a prior Codex thread)

Send only the delta instruction on resume; options go **before** the `resume`
subcommand (verified `codex-cli 0.142`: `codex exec [OPTIONS] resume <id|--last>`):

```bash
codex exec --disable plugins -s read-only resume <SESSION_ID> "Re-check the fixes for regressions" < /dev/null
codex exec --disable plugins -s read-only resume --last "Re-check the fixes for regressions" < /dev/null
```

`<SESSION_ID>` is printed as `session id:` in each run's header; `--last` continues the
most recent session instead. Don't restate the whole prompt unless the direction
changed materially.
