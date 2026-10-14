---
name: peekaboo
description: "Use Peekaboo for macOS screenshots, Accessibility inspection, and background app/window/UI automation, including fallback computer use when the primary tool cannot handle an authorized task."
---

# Peekaboo

Use native Peekaboo commands for macOS apps, windows, menus, dialogs, browser chrome, and pixels. Prefer existing browser tooling for page content, DOM, forms, console, and network; Peekaboo's `browser` command is available when that integration is configured. Stay within the user's authorized task and verify the resulting UI.

For Peekaboo browser work, retain one Bridge host and its existing provider connection across calls. The pinned
Chrome DevTools MCP 1.10.1 is launched through Peekaboo's audited telemetry bootstrap; a bare upstream `npx` invocation
does not carry that fix. Background calls require an existing exact connection and retain the source-audited tool
allowlist. Page evaluation can grant web user activation even when Chrome remains behind another app, so do not
infer background safety from window focus alone or retry a refused call with foreground authority implicitly.

## Select the CLI and execution host

Use the installed signed CLI for ordinary automation; building Peekaboo is a development task, not a prerequisite. Honor an explicit binary override and inspect its version:

```bash
PB="${PEEKABOO_BIN:-$(command -v peekaboo)}"
"$PB" --version
"$PB" bridge status --verbose --json
"$PB" permissions status --all-sources --json
```

The CLI ships separately from `Peekaboo.app`. Keep the release archive's CLI and accompanying compatibility dylibs together. The app's executable is a GUI host, not the CLI; current releases reject CLI-style arguments before Bridge startup. Using the same current signed CLI/app release avoids capability drift, but compatibility is negotiated by protocol and operation capabilities, not simple version equality.

Host selection depends on the operation. Ordinary automation prefers a healthy reusable daemon, then a capable GUI host, before starting a daemon. Capture, AX inspection, browser, and snapshot-state work first prefer and may start the current CLI build's daemon. An explicit snapshot routes to its unique live producer; explicit socket or local-only overrides remain authoritative. Do not stop hosts merely because several candidates exist.

When app-held permissions are needed, launch the GUI host and pin the same socket for permission checks and observation:

```bash
open -gj -a Peekaboo
GUI_SOCKET="$HOME/Library/Application Support/Peekaboo/bridge.sock"
"$PB" bridge status --bridge-socket "$GUI_SOCKET" --verbose --json
"$PB" permissions status --bridge-socket "$GUI_SOCKET" --json
"$PB" see --bridge-socket "$GUI_SOCKET" --no-elements --mode screen --path /tmp/peekaboo-screen.png --json
```

`open -gj` requests a background/hidden launch; first-run onboarding or missing-configuration prompts can still activate the app. Verify the reported host rather than assuming it was selected. The GUI app, daemon, and caller-local CLI have separate TCC contexts. Screen Recording is checked where capture runs, Accessibility where AX runs, and Event Synthesizing where events are sent. Both local and Bridge sources need not have identical grants.

## Observe, target, act, verify

1. Resolve the target with `app list` and `window list`; prefer exact PID/window IDs over broad app names or titles.
2. Observe with pixels, Accessibility, or both. Ordinary `see` does not activate the target; `--web-focus` explicitly permits a focus action and is not a read-only retry.
3. Copy opaque element and snapshot IDs from that observation. Prefer an element click, `set-value` for an intended value replacement, or a suitable state-only AX action over coordinate input.
4. Use background delivery with an exact target. Add `--foreground` when shared-desktop interaction is authorized and needed; do not silently promote a refused background command.
5. Read the canonical outcome and verify the intended change with a fresh `see`, `verify`, or other readback. A successful dispatch alone does not prove the app changed.

```bash
"$PB" app list --include-hidden --include-background --json
"$PB" window list --app Safari --json

# Read clipboard contents only when relevant to the authorized task.
"$PB" clipboard get --json

# Pixels only; an exact window also publishes a coordinate receipt.
"$PB" see --window-id "$WINDOW_ID" --no-elements --path /tmp/peekaboo-window.png --json

# Pixels and element IDs, with an annotated artifact.
"$PB" see --window-id "$WINDOW_ID" --annotate --path /tmp/peekaboo-elements.png --json

# AX text and IDs without screenshot capture.
"$PB" see --window-id "$WINDOW_ID" --tree --no-screenshot --json

# Use IDs from the applicable fresh observation, not all examples in sequence.
"$PB" click --on "$ELEMENT_ID" --snapshot "$SNAPSHOT_ID" --json
"$PB" scroll --direction down --on "$ELEMENT_ID" --snapshot "$SNAPSHOT_ID" --json
```

After a mutation changes the UI, capture again before using IDs for another action. `requires_fresh_observation: true` consumes the snapshot for mutation. Partial, indeterminate, and unverified results may already have changed the app; never repeat input blindly. Inspect image contents to verify capture and visual results. `sips -g pixelWidth -g pixelHeight <path>` checks dimensions only.

## Background input and coordinates

Background `click` can invoke an element's AX action or focus a writable text field without activating its app. `--input-strategy actionOnly` selects the AX route; coordinate clicks can also use it by hit-testing a pressable AX element. Generic `action AXPress` and `action AXShowMenu` require `--foreground`; only generic `AXIncrement`/`AXDecrement` are background-safe. Prefer dedicated `click` for background activation.

Background typing/paste accept exact window routes even when the app has several windows. App/PID-only routes require a complete inventory with at most one eligible window. Prefer a fresh exact-window snapshot for `type`; it must identify the focused field in the intended internal key window. If needed, click the field, observe again, then type using the new snapshot. Exact routes revalidate process generation, window bounds, and focus. AX text edits need Accessibility; event fallback needs Event Synthesizing.

```bash
"$PB" type "text" --snapshot "$SNAPSHOT_ID" --json
"$PB" press Return --app TextEdit --window-id "$WINDOW_ID" --json
"$PB" paste "text" --app TextEdit --window-id "$WINDOW_ID" --json
```

`type` normally succeeds only for a confirmed change. It can return non-success after accepted dispatch, so read the outcome before retrying. Scripts doing their own follow-up observation may opt into `--accept-dispatched`; this does not confirm delivery. Raw background `press` needs an exact window selector or fresh exact-window snapshot; app/PID-only chords require `--foreground`. Default background-only Agent/MCP typing is stricter than the direct CLI: it requires a fresh exact non-dialog snapshot without competing selectors.

Background `scroll` accepts an element `--on` or coordinates `--at x,y`; app/window flags alone are insufficient. Coordinates require an explicit fresh screenshot `--snapshot` (never `latest`) and a protocol-1.43 host advertising `backgroundCoordinateScroll`. CLI points are window-local logical points; `--global` changes the basis without granting foreground authority. MCP `coords` defaults to global display points; image/normalized points use the observation's explicit `coordinate_reference`. Older hosts refuse without fallback.

Coordinate scrolling prefers the nearest proven AX scroll owner and can use exact-window wheel delivery on eligible native-WebKit surfaces without an exposed owner. Preserve unverified/retry-unsafe outcomes and verify the intended region actually moved. Targetless scrolling, `--smooth`, and nonzero `--delay` need `--foreground` and cannot be combined with `--at`. Shared-cursor `move`, targetless keyboard input, and `click --long-press` also require explicit foreground mode.

Background `drag` requires an explicit fresh `--snapshot`, with both endpoints inside its exact window. Use global logical coordinates or element IDs from that snapshot, a linear path, 1–10000 ms duration, and 1–96 samples. Protocol 1.39 hosts support this window-routed gesture without moving the physical cursor or activating the app; older hosts refuse without foreground fallback. Dispatch remains unverified and retry-unsafe, including an interrupted gesture: observe before another input. Cross-window/app drops, modifiers, human profiles, and app/window selector flags require explicit `--foreground`.

`click --at` uses logical points. Background coordinates are relative to the snapshot window even without target flags; add `--global` for global logical coordinates inside that window. Foreground coordinates are window-relative with target flags and global without them. Ordinary `see` produces logical1x images; do not divide their coordinates by a Retina scale. For `--retina`, crops, or resized previews, use the capture's coordinate metadata and `screen list` bounds/scale to map pixels to logical points.

```bash
"$PB" see --window-id "$WINDOW_ID" --no-elements --path /tmp/peekaboo-click.png --json
# Copy the returned snapshot ID before clicking window-local logical points.
"$PB" click --window-id "$WINDOW_ID" --at 20,40 --snapshot "$SNAPSHOT_ID" --json
```

Background coordinate clicks require a fresh screenshot snapshot with an exact process/window/bounds receipt; AX-only observations are insufficient. Moved, replaced, or unverifiable targets fail before dispatch. Background right/double/middle/triple clicks can use exact routed events, but completed dispatch remains effect-unverifiable. Observe before deciding whether another click is needed.

## Troubleshooting and references

- Capture permissions belong to the executing host. Compare `permissions status --all-sources`, then pin the intended host for diagnostics and capture. Request only permissions needed for the selected operation; do not replace signed installs with ad-hoc builds against saved TCC/Keychain state.
- ScreenCaptureKit coordination is scoped to Peekaboo's own CLI/app processes and selected Bridge hosts. Other apps such as Claude, OpenClaw, Zoom, or OBS may run concurrently without blocking capture. Explicit `see --capture-engine classic` (alias `cg`) avoids in-process ScreenCaptureKit on the selected host; all engines still require valid capture permission evidence there.
- Prefer Bridge capture from SSH or background launchd sessions. `--no-remote --capture-engine cg` is a caller-local diagnostic for a known active Aqua session; elsewhere it can return wallpaper-only or redacted pixels despite reporting success.
- If a concrete snapshot's producer is unavailable or an explicit host does not own it, observe again on the intended host. Do not substitute an unrelated snapshot or weaken the target merely to retry.
- Use `capture live` for change-aware capture and `capture video` to sample an existing video. Store task captures under an explicit temporary path and inspect/redact them before any authorized sharing.
- Discover current syntax with `<command> --help`, `learn`, `tools --json`, and `tools describe <name> --json` (MCP schema, not CLI flags). Timing options accept bare milliseconds or `ms`/`s`; prefer explicit suffixes.
- v4 uses noun inventories (`app list`, `window list`, `screen list`), `see`, `press`, `action`, and `click --at`; use live help when translating older examples.

Canonical references stay usable when this skill is linked into another repository or agent directory:

- [Command index](https://github.com/openclaw/Peekaboo/blob/main/docs/commands/README.md), especially [type](https://github.com/openclaw/Peekaboo/blob/main/docs/commands/type.md), [click](https://github.com/openclaw/Peekaboo/blob/main/docs/commands/click.md), and [scroll](https://github.com/openclaw/Peekaboo/blob/main/docs/commands/scroll.md).
- [Bridge host](https://github.com/openclaw/Peekaboo/blob/main/docs/bridge-host.md), [permissions](https://github.com/openclaw/Peekaboo/blob/main/docs/permissions.md), and [subprocess integration](https://github.com/openclaw/Peekaboo/blob/main/docs/integrations/subprocess.md).
- For Peekaboo development, read the checkout's [AGENTS.md](https://github.com/openclaw/Peekaboo/blob/main/AGENTS.md) and [building guide](https://github.com/openclaw/Peekaboo/blob/main/docs/building.md); follow their source-build and test workflow for code changes.

## Local overlay (user policy + verified v4 traps)

Everything above is upstream's skill, unmodified, from `openclaw/Peekaboo@5f297f1bf` (v4.9.2). This section is the user's overlay: local policy plus traps verified live on Peekaboo 4.9.2 (CLI + Peekaboo.app 4.9.2, daemon host, all grants, 2026-10-13). Items marked *(source)* were confirmed from 4.9.2 source but not run live. When upstream and this section disagree, trust the installed build's `--help` and re-run the smoke test below; then fix whichever text is wrong.

### Policy

- **Never send captures to an external AI.** Avoid `see --analyze`, MCP `analyze`, and `agent` with a cloud `--model`. Capture to an explicit `/tmp` path and `Read` the file for local vision. Crop with `sips` before reading when only a region matters.
- Treat AX trees, menu dumps, window titles, and Chrome tab labels as private. Do not paste them anywhere external.
- Don't disturb the user's foreground work: stay in background mode, and never add `--foreground` without a task reason.

### Picking the tool

| Task | Use |
|---|---|
| Evidence screenshot of a window whose ID you know | `screencapture -x -o -l <window_id> /tmp/x.png` (~0.3s vs ~1.9s, but a 2× Retina image) |
| Find a window ID, or get a 1× image (fewer vision tokens) | `peekaboo window list --app X --json`, then `peekaboo see --window-id <id> --no-elements --path /tmp/x.png` |
| Read native app state/text | `peekaboo see --window-id <id> --tree --no-screenshot --json` |
| Click/type in a background native app | Peekaboo: fresh observation → `click`/`type`/`set-value` → re-observe |
| Web page content, DOM, forms | Claude-in-Chrome by default; Peekaboo `browser` only when its bridge is configured (see upstream above) |
| Fixed, high-volume, known-target flow | a small JXA (`osascript -l JavaScript`) AX script (measured: 5 background presses 3.6s vs Peekaboo 5.8s), but it skips Peekaboo's stale-target and process checks — use only on low-stakes targets |

### Install / parity (both Macs)

- `brew install openclaw/tap/peekaboo` (the old `steipete/tap` stopped at 4.5.0). Keep Peekaboo.app on the same release.
- MCP: Claude `claude mcp add -s user peekaboo -- /opt/homebrew/bin/peekaboo mcp`; Codex `[mcp_servers.peekaboo] command = "/opt/homebrew/bin/peekaboo", args = ["mcp"]`. Never `npx @steipete/peekaboo` (version drift; lacks the audited browser fix).
- *(source)* MCP is stdio-only and never hosts a Bridge listener; `--bridge-socket` attaches to an existing host.
- MCP is background-only unless the server is started with `--allow-foreground` (and `--allow-temporary-clipboard` for temporary paste). Keep the default.
- `tools` lists the policy-filtered catalog (26 by default on 4.9.2; the source defines 28). There is no MCP `list` tool in v4.

### Verified v4 traps

- **Removed 3.x commands fail with a migration hint.** `list` → `app list` / `window list` / `screen list`; `image` → `see --no-elements`; `inspect-ui` → `see --tree --no-screenshot` (MCP keeps `inspect_ui`); `perform-action` → `action`; `hotkey` → `press`; `swipe` → `drag`; `open` → `/usr/bin/open` or `app launch --open`; `run`/`sleep` → shell. Renamed flags: `--coords` → `--at`, `--timeout-seconds` → `--timeout`.
- **A snapshot that drove a mutation is consumed.** Reusing it returns `SNAPSHOT_STALE`. Observe again before every action. A fabricated ID returns `SNAPSHOT_NOT_FOUND`. A snapshot that doesn't match `--pid`/`--app`/`--window-id` returns a specific `VALIDATION_ERROR`.
- **A background `action AXPress` is refused** ("requires --foreground"). For background activation use `click --on <id> --snapshot <id>`; the result reports `deliveryMode: background`.
- **`click --input-strategy actionOnly` stayed on the daemon and succeeded** with a daemon snapshot (the 3.6.0 local-routing bug is fixed for `click`). Source docs say a per-call `actionOnly` on `type` runs locally — not verified live.
- **`space list` fails on the remote daemon** ("remote Space support is not implemented"). Use `space list --no-remote`; it lists all Spaces with `is_active`.
- **There can be two daemons:** `daemon.sock` and a build-specific `daemon-<hash>.sock` (observed: `see --tree` used the latter). Hosts are chosen per operation — read the real host from `bridge status --verbose --json` or the `Runtime host:` line in `debug_logs`, not `daemon status`.
- **Key casing still varies by command.** `app list` (`data.apps`) and `window list` (`data.windows`, plus `inventory_completeness`) use snake_case. `screen list` and `menubar list` (`data.items`) use camelCase. Inspect the keys; a wrong key silently yields nothing.
- **`window list` needs `--app` or `--pid`.** There is no global window search: enumerate `app list` first.
- *(source)* **Explicit capture choices fail closed:** an explicit `--capture-engine` or ScreenCaptureKit ownership choice errors before dispatch rather than silently falling back.
- *(source)* **Inventory fails closed:** an app-inventory timeout or incomplete validation is an error, not an empty desktop.
- **`app list` hides background apps by default** (11 vs 103 with `--include-background`). Resolving a daemon or helper requires `--include-background --include-hidden`.
- **Rendered values can be empty in AX** (e.g. Calculator's display `value` came back empty). Verify with a screenshot + `Read`.
- **`see --json` without `--path`** keeps the image in managed storage and returns null screenshot paths. Pass a `/tmp` path when you need the file.
- **Chrome tabs** show up in `see --app "Google Chrome" --tree --no-screenshot` as `AXRadioButton`s with the title in both `label` and `description`. Tab clicking was not live-tested; use the normal fresh-snapshot element-ID workflow.
- **Visualizer / Ghost HUD needs Peekaboo.app running.** `peekaboo visualizer` fails clearly without it. *(source)* The typed-text mask is read from the sending process's environment, and targeted background input emits no HUD.
- *(source)* `app quit` accepts a positional name or `--app`/`--pid`, refuses to quit the selected daemon host, and fails the whole envelope if any nested result fails. Still prefer the bundle ID `boo.peekaboo.mac` for the GUI app.
- *(source)* Plain-text background `paste` types directly and may not touch the clipboard. Check `clipboardCleanupStatus`, not just `restoreSucceeded`.

### Smoke test after any upgrade

```bash
PB="$(command -v peekaboo)"; "$PB" --version
"$PB" permissions status --all-sources --json
"$PB" bridge status --verbose --json
open -ga Calculator
WID=$("$PB" window list --app Calculator --json | ruby -rjson -e 'puts JSON.parse(STDIN.read).dig("data","windows",0,"window_id") || abort("no Calculator window")') || exit 1
for B in AllClear One Add Two Equals; do
  IDS=$("$PB" see --window-id "$WID" --tree --no-screenshot --json |
    ruby -rjson -e 'd=JSON.parse(STDIN.read)["data"]; e=d["ui_elements"].find{|x| x["identifier"]==ARGV[0]} or abort("no #{ARGV[0]}"); puts "#{d["snapshot_id"]} #{e["id"]}"' "$B") || exit 1
  read -r SNAP EL <<<"$IDS"
  "$PB" click --on "$EL" --snapshot "$SNAP" --json | ruby -rjson -e 'j=JSON.parse(STDIN.read); puts "#{ARGV[0]} #{j["success"]} #{j.dig("data","deliveryMode")}"' "$B"
done
"$PB" click --on "$EL" --snapshot "$SNAP" --json | ruby -rjson -e 'puts JSON.parse(STDIN.read).dig("error","code")'   # expect SNAPSHOT_STALE
"$PB" see --window-id "$WID" --no-elements --path /tmp/pb-calc.png --json   # Read it: expect "1+2" / "3"
```

Expect: background `deliveryMode`, `SNAPSHOT_STALE` when a consumed snapshot is reused, and the frontmost app unchanged. If any trap above no longer reproduces, update this section.
