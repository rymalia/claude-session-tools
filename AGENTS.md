# Repository Guidelines

## Project Structure & Module Organization

This repository is a dual-host Claude Code and OpenAI Codex plugin marketplace, not an application package. The Claude marketplace manifest lives at `.claude-plugin/marketplace.json`; the Codex marketplace manifest lives at `.agents/plugins/marketplace.json`. The active plugin is `plugins/session-tools/`, with host manifests at `plugins/session-tools/.claude-plugin/plugin.json` and `plugins/session-tools/.codex-plugin/plugin.json`.

Claude Code slash commands (`/now`, `/replay`, `/replay-merge`) are Markdown files in `plugins/session-tools/commands/`. Skills live under `plugins/session-tools/skills/`; `session-summary` is a dual-host skill (Claude Code `/session-tools:session-summary`, bare `/session-summary` while unclaimed; Codex `$session-tools:session-summary`) that bundles its own metadata script at `plugins/session-tools/skills/session-summary/scripts/collect-metadata.sh`, referenced via `${CLAUDE_SKILL_DIR}`. Shared hook configuration is in `plugins/session-tools/hooks/hooks.json`, with host-specific handling dispatched by `plugins/session-tools/scripts/session-start.sh`. Other shared scripts live in `plugins/session-tools/scripts/`. Long-form reference notes and generated session summaries live under `docs/`.

## Build, Test, and Development Commands

There is no package manager, build step, or formal test suite. Use focused syntax checks:

```bash
python3 -m py_compile plugins/session-tools/scripts/extract-session.py
python3 -m py_compile plugins/session-tools/scripts/codex-session-state.py
bash -n plugins/session-tools/scripts/session-start.sh
bash -n plugins/session-tools/scripts/session-start-time.sh
bash -n plugins/session-tools/skills/session-summary/scripts/collect-metadata.sh
```

To smoke-test metadata output locally:

```bash
bash plugins/session-tools/skills/session-summary/scripts/collect-metadata.sh
```

To exercise replay without installing the plugin:

```bash
python3 plugins/session-tools/scripts/extract-session.py <session-id-or-path>
```

## Coding Style & Naming Conventions

Keep files dependency-free and portable. Bash scripts should use clear, quoted variable expansions and avoid unnecessary external dependencies. Python should remain standard-library only and favor readable dataclasses/functions over framework code. Command files should be concise Markdown contracts with explicit steps and failure handling.

Plugin versions must stay synchronized between `.claude-plugin/marketplace.json`, `plugins/session-tools/.claude-plugin/plugin.json`, and `plugins/session-tools/.codex-plugin/plugin.json`.

## Testing Guidelines

Validate scripts before proposing changes. For behavior changes, test against real Claude session data when available: a normal `.jsonl` transcript, a folder-only session with subagents, and an index-only session if relevant. Document manual verification in the change notes or PR description.

## Commit & Pull Request Guidelines

Recent commit messages use short, descriptive subjects, often scoped by release, for example `session-tools v1.3.0 — stamp Claude Code session id into summary frontmatter` or `docs: add Claude Code session-storage reference`. Keep commits focused: separate docs-only changes from plugin behavior changes when practical.

Pull requests should explain the user-facing command or hook behavior changed, list validation commands run, note any version bumps, and call out compatibility concerns for installed plugin users.

## Agent-Specific Instructions

Do not overwrite generated session summaries or untracked docs unless explicitly asked. Preserve the existing Claude plugin layout when adding future Codex support; add parallel metadata rather than replacing `.claude-plugin` files.
