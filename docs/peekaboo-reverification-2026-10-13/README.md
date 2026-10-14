# Peekaboo skill: 3.6 → 4.9.2 reverification (2026-10-13)

Why `skills/peekaboo/SKILL.md` looks the way it does, and how to refresh it.

## Structure of the skill

- **Top:** upstream's `skills/peekaboo/SKILL.md`, unmodified, from `openclaw/Peekaboo@5f297f1bf` (v4.9.2).
- **Bottom:** `## Local overlay`, which holds local policy plus v4 traps verified live on 4.9.2.

Upstream's own `docs/agent-skill.md` asks distributors to work this way: the upstream skill owns product behavior, and the overlay holds only host policy and deployment details. Our 3.x skill was a fork of upstream's old 34-line skill, so each release silently made parts of it stale. Under this structure a refresh doesn't need a text merge: replace the upstream half, then re-run the overlay's smoke test.

## Refresh procedure (each Peekaboo release)

1. `brew upgrade openclaw/tap/peekaboo` and update Peekaboo.app to the same release.
2. In `~/projects/Peekaboo`: `git fetch upstream && git merge --ff-only upstream/main` (main is a clean upstream tracker; pushes to `upstream` are disabled).
3. Replace everything above `## Local overlay` with `git show upstream/main:skills/peekaboo/SKILL.md`, and update the commit/version in the overlay's first paragraph.
4. Run the overlay's smoke test, then spot-check the traps. Drop the ones upstream now covers or that no longer reproduce.
5. Have a Codex review check the overlay against `upstream/main` source.

## What the reverification found

32 claims from the 3.6.0 overlay (`01-claims-3.6.md`) were checked two ways: live on 4.9.2 (`02-…`) and against the source by Codex gpt-5.6-luna (`03-…`). Where the two disagreed, I re-checked live.

- **Removed or renamed in v4:** `list`, `image`, `inspect-ui`, `perform-action`, `hotkey`, `open`, `swipe`, `run`, `sleep`, `--coords`, `--timeout-seconds`, and the MCP `list` tool.
- **Behavior reversed:** reusing a snapshot after a mutation is now refused (`SNAPSHOT_STALE`); a background `action AXPress` is now refused without `--foreground`.
- **3.x bugs fixed upstream:** `actionOnly` click routing; `inspect-ui`'s fabricated-snapshot fallback to the frontmost app; generic mismatch errors (now specific `VALIDATION_ERROR`s); empty-success inventories (inventory now fails closed).
- **Still true and kept:** JSON key casing varies by command; no global window search; `app list` background filter; AX `value` can be empty; `see --json` without `--path` keeps the image private; the visualizer needs Peekaboo.app.
- **New v4 traps:** `space list` needs `--no-remote`; two daemon sockets can coexist; `tools` lists the policy-filtered catalog (26 of 28 tools).

## Peekaboo vs. native tools (`04-…` plus live benchmark)

Measured on the same Calculator window (M3 MacBook Air):

| Operation | Peekaboo 4.9.2 | Native |
|---|---|---|
| Window screenshot | 1.85s, 1× (230×408) | `screencapture -x -o -l` 0.30s, 2× (460×816) |
| AX tree | 1.1s, 16 KB JSON with IDs, labels, bounds, snapshot | `osascript` `entire contents`: 1.1s, 3.5 KB of bare element paths |
| 5 background presses | 5.8s (fresh `see` + `click` each) | JXA `AXPress`: 3.6s |
| Stale or wrong target | refused (`SNAPSHOT_STALE`, process and window checks) | no protection |
| Background `AXPress` | refused without `--foreground` (policy) | allowed |
| Permissions held by | daemon and Peekaboo.app | whatever terminal hosts the agent |

Conclusions:

- Use **`screencapture`** for evidence shots of a known window.
- Use **Peekaboo** to find windows and for observe → act → verify loops on native apps. Its overhead buys stale-target safety.
- Use **Claude-in-Chrome** for page content.
- Use **raw JXA/AX** only for fixed, low-stakes flows.
- Avoid **Claude or Codex computer use** wherever screenshots must stay local or focus must not move.

Two caveats from the benchmarking:
- Plain AppleScript `entire contents` filtering failed twice on syntax. JXA's recursive walk worked first time.
- Codex called System Events output "the largest" without measuring it; on Calculator it was the smallest but the least usable.
