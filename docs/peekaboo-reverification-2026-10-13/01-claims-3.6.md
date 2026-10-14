# 3.x overlay claims to re-verify on Peekaboo 4.9.2

Source of claims: `git show local/skills-3.6:skills-per-agent/claude/peekaboo/SKILL.md` (verified on 3.6.0).
Upstream v4 skill: `git show upstream/main:skills/peekaboo/SKILL.md`.

C1  MCP exposes "the same 27 core tools", not admin commands (daemon, bridge, learn, tools, config).
C2  Setup tip: point MCP at `/opt/homebrew/bin/peekaboo mcp` to avoid npx drift.
C3  `peekaboo learn` can list more tools than `peekaboo tools`; treat `tools`/`--help` as authoritative.
C4  `inspect-ui` (CLI) / `inspect_ui` (MCP) = AX text; `see` = pixels + elements.
C5  `app list --json`: records under `data.apps`, snake_case (`name`,`bundle_id`,`pid`,`is_active`,`is_hidden`); excludes background by default; `--include-background`/`--include-hidden`. Legacy `list apps`: camelCase under `data.applications`.
C6  `app launch <Name>` positional, but `app quit` requires `--app <Name>`; each rejects other form.
C7  Bare `list windows --app X --json` = richest record (17 fields, `window_id`); `--include-details bounds,ids` = leaner 8-field projection renamed `windowID`.
C8  `window list --app X --json` = AX-only, 5-field snake (`window_id`,`window_title`,`window_index`,`bounds`,`is_on_screen`); works when Screen Recording fails.
C9  No global window search; `list windows` needs a target app.
C10 Chrome tabs AX-enumerable via `inspect-ui --app-target "Google Chrome"`; tab title in `desc`; click matcher searches label/identifier not desc → click by elem id.
C11 `browser` needs opt-in: Chrome 144+, chrome://inspect remote debugging, `browser connect`.
C12 `menu list --app X --json` works for background app, key `menu_structure`; `list menubar --json` fields ownerName/axIdentifier/bundleIdentifier/axDescription/frame/isVisible.
C13 `agent` models incl. minimax/MiniMax-M3, kimi/*; `agent --dry-run` still needs API key.
C14 Screen-Recording gating is host-context-dependent; `list apps` routes local in-process even with healthy bridge; diagnose with `bridge status --json`; `permissions status` vs `list permissions` can disagree.
C15 Background `click --input-strategy actionOnly` can return success:true without mutating; `app list`/`space list`/`list menubar` can succeed with zero results.
C16 `app quit --app Peekaboo` matches CLI process; top-level success:true, nested results[0].success:false; use `boo.peekaboo.mac`.
C17 `list windows` returns more than `windowCount` (popovers etc.); filter non-empty title.
C18 `inspect-ui --json` shape = `data.content[].text` + `data.meta.element_count`; `see --json` = `data.ui_elements` with bounds.
C19 Mutations invalidate implicit `latest` but not explicit snapshot history; `click` on fabricated snapshot → SNAPSHOT_NOT_FOUND, PID mismatch → INVALID_INPUT; `inspect-ui` with fabricated `--snapshot` silently recaptures (frontmost app without --app-target).
C20 Element IDs opaque, differ across snapshots.
C21 JSON key casing varies by command and flag.
C22 `--input-strategy actionOnly` forces click to local in-process host → SNAPSHOT_NOT_FOUND for daemon/GUI-host snapshots; `--bridge-socket` doesn't fix.
C23 `see --json` without `--path` keeps image in managed storage, returns empty screenshot paths.
C24 `capture action` can report success with non-overlapping capture window.
C25 `space list` shows only active Space; `space list`/`list menubar` env-flaky.
C26 On-demand daemon at ~/Library/Application Support/Peekaboo/daemon.sock, idles out ~300s; `daemon run` vs `daemon start`; read host from `Runtime host:` debug line / `bridge status`; MCP `image` window capture hang (no longer reproduced on 3.6.0).
C27 Ghost HUD needs Peekaboo.app; `peekaboo visualizer` fires 15-event smoke; errors without app; PEEKABOO_VISUALIZER_MASK_TYPED_TEXT must be in app env, not CLI env.
C28 Privacy: `agent` (cloud model), `analyze`, `--analyze`, `--question` on see/image send captures externally.
C29 `perform-action --on ID --action AXPress --snapshot S` exists and is the clean UIAX smoke test.
C30 `paste "text" --app X --json` one-shot; restores clipboard; reports `restoreSucceeded`.
C31 Flags used in workflows: `see --path`, `see --timeout-seconds`, `click --on --snapshot`, `click --focus-background`, `--foreground`, `--input-strategy actionOnly|synthOnly`.
C32 Negative control: `click --coords 10,10 --input-strategy actionOnly` is rejected (coords cannot use actionOnly).
