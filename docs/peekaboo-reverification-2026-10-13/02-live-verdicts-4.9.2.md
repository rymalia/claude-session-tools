# Live verdicts on Peekaboo 4.9.2 (M3 MacBook Air, 2026-10-13, daemon host, all grants)

| Claim | Live verdict | Evidence |
|---|---|---|
| C1 | CHANGED | MCP catalog = 26 tools; `list` tool removed (app/window/space instead) |
| C2 | STILL-TRUE (applied) | Claude MCP repointed to brew binary; npx served 4.9.2 while brew was 4.5.0 |
| C3 | NOT OBSERVED | `learn` mentions no removed commands; drop or keep as soft note |
| C4 | OBSOLETE (form) | `inspect-ui` removed → `see --tree --no-screenshot` |
| C5 | CHANGED | `list apps` removed. `app list` still `data.apps` snake_case (+`process_start_identity`), routes via daemon; 11 default / 12 hidden / 103 background |
| C6 | STILL-TRUE | `app launch [<app>]` positional; `app quit --app/--pid` (+`--expected-process-start-identity`) |
| C7 | OBSOLETE | `list windows` removed |
| C8 | CHANGED | `window list --app` is now the primary window inventory: 10 fields (`window_id`,`window_title`,`window_index`,`bounds`,`is_on_screen`,`is_frontmost`,`is_key`,`layer`,`subrole`,`observation_capability`) + `inventory_completeness`/`inventory_warnings`; routes via daemon |
| C9 | STILL-TRUE | `window list` w/o `--app`/`--pid` → "Either --app or --pid must be specified" |
| C10 | CHANGED | `see --app "Google Chrome" --tree --no-screenshot`: 12 tabs as AXRadioButton/role `checkbox`; `label` AND `description` populated (title-in-desc-only trap likely gone; tab click not exercised) |
| C11 | not tested | (browser bridge left alone) |
| C12 | STILL-TRUE / CHANGED | `menu list --app` (background app) ok, `menu_structure`; `list menubar` → `menubar list`, list under `items`/`menu_bar_items`, camelCase fields |
| C13 | CHANGED | `agent --dry-run` succeeds without API key env; model list now minimax-m2.7 etc., MiniMax-M3/kimi not listed |
| C14 | OBSOLETE (as written) | app/window inventory route via daemon here; grant-less context not tested |
| C15 | partially | default background clicks verified by screenshot (1+2=3); success≠effect principle covered upstream |
| C16 | NOT RUN (unsafe) | could kill other sessions' `peekaboo mcp` processes |
| C17 | OBSOLETE | `list windows` removed |
| C18 | OBSOLETE | `see --tree` returns same `data.ui_elements` w/ bounds |
| C19 | REVERSED | explicit snapshot reuse after mutation → `SNAPSHOT_STALE`; fabricated → `SNAPSHOT_NOT_FOUND`; `see` no longer takes `--snapshot` so fabricated-snapshot frontmost fallback is gone; pid/app/window mismatch → clear `VALIDATION_ERROR` |
| C20 | STILL-TRUE | ids `elem_N`, snapshot `ps1_<hex>`; treat opaque |
| C21 | STILL-TRUE | `app list`/`window list` snake; `screen list`/`menubar list` camel |
| C22 | OBSOLETE (fixed) | `click --input-strategy actionOnly` with daemon snapshot → success, background, remote host |
| C23 | STILL-TRUE | `see --json` w/o `--path` → screenshot_raw/annotated null |
| C24 | not tested | |
| C25 | CHANGED | `space list` on remote host → error "remote Space support is not implemented"; `--no-remote` works and lists 2 Spaces |
| C26 | CHANGED | `daemon status` mode `auto`; TWO daemons: `daemon.sock` and build-specific `daemon-<hash>.sock` (see --tree used the latter); idle timing not measured |
| C27 | STILL-TRUE | visualizer w/o app: "Ensure Peekaboo.app is running and visual feedback is enabled" |
| C28 | CHANGED | `analyze` CLI command gone; `see --analyze` exists; `--question` absent; MCP still exposes `analyze` + `agent` tools |
| C29 | REVERSED | background `action AXPress` → VALIDATION_ERROR requires `--foreground`; `perform-action` → `action`; use `click` for background |
| C30 | not tested (clipboard safety) | |
| C31 | CHANGED | `--timeout-seconds` → `--timeout`; `--focus-background` still exists |
| C32 | CHANGED | `--coords` removed → `--at` (+ `--global`) |
| extra | STILL-TRUE | AX `value` of Calculator display empty → screenshot + Read still needed; `see` images are logical 1x |
| migration | VERIFIED LIVE | `list`, `image`, `inspect-ui`, `perform-action`, `hotkey`, `open`, `swipe`, `run`, `sleep` each → "Command 'peekaboo X' was removed in v4. Use '…'"; `click --coords` → "Option '--coords' was removed in v4" |
| bench | MEASURED LIVE | Calculator window: `screencapture -x -o -l` 0.30s (460×816) vs `peekaboo see --no-elements` 1.85s (230×408); 5 background presses: JXA AXPress 3.56s vs peekaboo 5×(see+click) 5.78s; both left the frontmost app unchanged |
| tap | VERIFIED | `steipete/homebrew-tap` Formula/peekaboo.rb pins v4.5.0; `openclaw/homebrew-tap` pins v4.9.2 (2026-10-13) |
