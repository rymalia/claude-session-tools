## Bottom line

[Inference] Peekaboo is the right control plane when an agent must inspect and mutate native macOS apps without taking focus, target a specific window safely, and verify outcomes. It is unnecessary overhead for isolated screenshots or fixed, high-volume scripts.

[Fact] Peekaboo combines capture, AX inspection, and native automation; its bridge/daemon can hold TCC grants separately from the terminal process (`README.md:5`, `docs/bridge-host.md:11,31-46`). Its workflow explicitly supports observe → exact target → background action → fresh verification (`skills/peekaboo/SKILL.md:43-49`).

### Decision table

| Task | Recommended tool | Why |
|---|---|---|
| Quick evidence screenshot of one known window | `screencapture -l <windowid> -x` | Lowest setup and likely lowest latency when the window ID is already known. |
| Full screen | `screencapture -x` | Direct, faithful pixel capture; no AX/bridge overhead. |
| Read text/state of a native app | Peekaboo `see --tree --no-screenshot` | Structured AX output without sending a screenshot into the agent context (`skills/peekaboo/SKILL.md:64-65`). |
| Click a button in a background app | Peekaboo exact-window snapshot + `click` | Supports background AX/input delivery and process/window validation (`skills/peekaboo/SKILL.md:76-78`). |
| Type into a field | Peekaboo exact-window `type` or `set-value` | Revalidates process generation, bounds, and focus; avoids blindly typing into the foreground app. |
| Menu-bar/menu interaction | Peekaboo `menu`/`menubar` | Gives a semantic menu surface; use foreground only where the menu implementation requires it. |
| Web page content/forms | Claude-in-Chrome DOM extension | DOM/state is more precise and token-efficient than pixels or browser AX. Peekaboo is better for browser chrome. |
| “Is X visible?” / “Did it change?” | Peekaboo capture plus local image/state comparison | Exact target, local file inspection, and fresh post-action observation; `capture live` supports change-aware capture. |
| Scripted repeatable flow | Small signed Swift helper | Best latency, smallest output, and full control when targets and assertions are known. Use Peekaboo when the flow must adapt to changing UI. |
| Generic screenshot-coordinate computer use | Peekaboo MCP/CLI | Claude computer use and Codex computer use are poor fits if screenshots may leave the machine or foreground focus must not move. |

[Fact] Peekaboo’s background input carries exact-window/process evidence and rejects drift or recycled targets (`docs/bridge-host.md:211-217,254-258,325`). A successful dispatch still requires verification; the project explicitly warns that dispatch success is not proof of state change (`skills/peekaboo/SKILL.md:49,72`).

### Comparative assessment

- Capture fidelity: `screencapture` and direct Swift provide the thinnest raw-pixel path. Peekaboo adds exact window/ROI metadata, silent background capture, and host-side file publication (`docs/bridge-host.md:199-201,258`).
- AX ergonomics/token cost: Peekaboo’s tree mode is agent-friendly. A hand-written Swift AX query can be even smaller; `System Events` + `entire contents` is usually the largest and noisiest output.
- Background behavior: Peekaboo is strongest. AppleScript can invoke AX actions in background, but keystrokes, menus, and activation frequently become focus-sensitive. Coordinate computer-use clients generally assume the visible desktop.
- TCC: native scripts need grants in the executing caller context. Peekaboo can route through a daemon or GUI bridge, but each Mac still needs grants for the selected host (`docs/permissions.md:21,25-32,63-79`). Keep the M3 and M4 on the same signed release and verify host selection; binary parity does not imply TCC parity.
- Latency/failure: native capture or a warm Swift process wins simple jobs. Peekaboo has cold-start, socket, host-selection, and protocol failure modes, but those buy safer targeting. Its docs note parallel enumeration and roughly two-second operation defaults (`docs/permissions.md:81-87`).
- Privacy: use Peekaboo’s file output and local inspection. Do not use `peekaboo agent`, image analysis, Claude computer use, or Codex computer use when their model path would transmit screenshots externally. Browser DOM is not equivalent to screenshot privacy; page contents can still be sensitive.

### Where Peekaboo is strictly worse than a native default

- One known window screenshot: `screencapture -l` has fewer processes, flags, and failure points.
- Full-screen or rectangular evidence: `screencapture -x` is simpler than host discovery plus snapshot metadata.
- High-rate capture/streaming: direct ScreenCaptureKit avoids Peekaboo’s IPC, receipt, and artifact-publication layers.
- A stable fixed workflow: signed Swift avoids Peekaboo CLI/MCP schema and daemon-version coordination.
- An app with no useful AX tree: Peekaboo cannot manufacture semantic controls; local vision or app-specific APIs are required.

### Top five risks

**`osascript` / JXA + System Events**

1. Focus theft: `activate`, `keystroke`, or menu operations can affect the user’s current app.
2. Stale/wrong targets: raw AX references lack Peekaboo’s process-generation and window-receipt checks.
3. TCC fragmentation: Automation, Accessibility, Terminal, script runner, and target-app identities can prompt or differ.
4. Tree explosion: `entire contents` creates high-token, slow, private dumps and can time out.
5. Partial effects: Apple Events can return late or ambiguously after an action already occurred; retrying can duplicate it.

**`screencapture`**

1. Pixels have no semantic control identity; an agent must infer coordinates or pair it with another unsafe actuator.
2. Capture and action are separate, so window movement, replacement, or PID reuse creates races.
3. Caller-context TCC failures can yield denied, redacted, or misleading captures in background sessions.
4. Retina/display scaling and changing rectangles can map visual coordinates incorrectly.
5. Files can capture unrelated private content and remain stale, misnamed, or accidentally exposed to the agent/model.