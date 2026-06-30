#!/usr/bin/env python3
"""Extract human-readable content from a Claude Code session JSONL transcript.

Session data for Claude Code lives under ~/.claude/projects/<slugified-cwd>/
in one of three on-disk layouts ("eras"):

    new     <session-id>.jsonl                               (main transcript only)
    middle  <session-id>.jsonl + <session-id>/subagents/     (main + companion)
    old     <session-id>/subagents/ only                     (folder-only; main
                                                              transcript was
                                                              cleaned up)

For folder-only sessions, the main transcript has been deleted by the default
cleanupPeriodDays=30 behavior but the per-subagent .jsonl files survive. This
script reconstructs as much of the conversation as possible by:

  1. loading the main transcript if it still exists,
  2. for folder-only sessions, loading every <uuid>/subagents/agent-*.jsonl,
  3. interleaving user prompts from ~/.claude/history.jsonl (a separate
     indefinitely-retained log) by matching sessionId, and
  4. merging all events by timestamp before rendering.

Usage:
    extract-session.py <session-id-or-path> [options]

The first positional argument may be a full UUID, a prefix (>=4 chars), an
absolute path to a .jsonl file, or an absolute path to a session folder.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import re
import signal
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError):
    pass  # SIGPIPE not available on Windows

SESSIONS_ROOT = Path.home() / ".claude" / "projects"
HISTORY_PATH = Path.home() / ".claude" / "history.jsonl"
CODEX_SESSIONS_ROOT = Path.home() / ".codex" / "sessions"

NOISE_TAGS = (
    "system-reminder",
    "local-command-stdout",
    "local-command-stderr",
    "local-command-caveat",
    "command-message",
    "command-args",
)
NOISE_RE = re.compile(
    r"<(" + "|".join(NOISE_TAGS) + r")\b[^>]*>.*?</\1>",
    re.DOTALL,
)
COMMAND_NAME_RE = re.compile(r"<command-name>\s*(/[^<\s]+)\s*</command-name>", re.DOTALL)


@dataclass
class SessionIndex:
    """Metadata from sessions-index.json for a single session."""
    summary: str | None = None
    first_prompt: str | None = None
    message_count: int | None = None
    created: str | None = None
    modified: str | None = None
    git_branch: str | None = None


@dataclass
class SessionBundle:
    """What we resolved from the user's argument."""
    session_id: str | None
    main_path: Path | None
    subagent_paths: list[Path] = field(default_factory=list)
    folder: Path | None = None        # <uuid>/ dir if present
    project_slug: str | None = None   # parent dir under ~/.claude/projects/
    index_meta: SessionIndex | None = None  # from sessions-index.json
    is_codex: bool = False            # OpenAI Codex CLI rollout transcript
    codex_meta: dict = field(default_factory=dict)  # session_meta payload bits

    @property
    def is_folder_only(self) -> bool:
        return self.main_path is None and bool(self.subagent_paths)


def load_session_index(project_dir: Path, session_id: str) -> SessionIndex | None:
    """Read sessions-index.json and return metadata for a given session."""
    idx_path = project_dir / "sessions-index.json"
    if not idx_path.is_file():
        return None
    try:
        data = json.loads(idx_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    for entry in data.get("entries", []):
        if entry.get("sessionId") == session_id:
            return SessionIndex(
                summary=entry.get("summary"),
                first_prompt=entry.get("firstPrompt"),
                message_count=entry.get("messageCount"),
                created=entry.get("created"),
                modified=entry.get("modified"),
                git_branch=entry.get("gitBranch"),
            )
    return None


def resolve_session(id_or_path: str) -> SessionBundle:
    """Turn the user's argument into a SessionBundle. Exits on error."""
    p = Path(id_or_path).expanduser()

    if p.is_file():
        is_sub = p.parent.name == "subagents" or p.name.startswith("agent-")
        if is_sub:
            # Subagent file — session_id will be sniffed from events.
            return SessionBundle(session_id=None, main_path=None, subagent_paths=[p])
        proj_dir = p.parent
        return SessionBundle(
            session_id=p.stem,
            main_path=p,
            project_slug=proj_dir.name if proj_dir.parent == SESSIONS_ROOT else None,
            index_meta=load_session_index(proj_dir, p.stem),
        )

    if p.is_dir():
        # <uuid>/ folder — could be middle-era (companion .jsonl exists) or
        # folder-only.
        sub_dir = p / "subagents"
        subs = sorted(sub_dir.glob("*.jsonl")) if sub_dir.is_dir() else []
        main_candidate = p.parent / f"{p.name}.jsonl"
        if main_candidate.is_file():
            return SessionBundle(
                session_id=p.name,
                main_path=main_candidate,
                subagent_paths=subs,
                folder=p,
                project_slug=p.parent.name,
                index_meta=load_session_index(p.parent, p.name),
            )
        if subs:
            return SessionBundle(
                session_id=p.name,
                main_path=None,
                subagent_paths=subs,
                folder=p,
                project_slug=p.parent.name,
                index_meta=load_session_index(p.parent, p.name),
            )
        sys.exit(f"error: {p} contains neither a main transcript nor subagent files")

    # Treat as UUID / prefix — search under SESSIONS_ROOT.
    if not SESSIONS_ROOT.is_dir():
        sys.exit(f"error: {SESSIONS_ROOT} does not exist")

    jsonl_matches = sorted(SESSIONS_ROOT.glob(f"*/{id_or_path}*.jsonl"))
    if len(jsonl_matches) > 1:
        sys.stderr.write(f"error: {id_or_path!r} matches multiple sessions:\n")
        for m in jsonl_matches:
            sys.stderr.write(f"  {m}\n")
        sys.exit(2)
    if len(jsonl_matches) == 1:
        main = jsonl_matches[0]
        proj_dir = main.parent
        companion = proj_dir / main.stem
        subs: list[Path] = []
        folder: Path | None = None
        if companion.is_dir():
            folder = companion
            sub_dir = companion / "subagents"
            if sub_dir.is_dir():
                subs = sorted(sub_dir.glob("*.jsonl"))
        return SessionBundle(
            session_id=main.stem,
            main_path=main,
            subagent_paths=subs,
            folder=folder,
            project_slug=proj_dir.name,
            index_meta=load_session_index(proj_dir, main.stem),
        )

    folder_matches = sorted(
        d for d in SESSIONS_ROOT.glob(f"*/{id_or_path}*") if d.is_dir()
    )
    if len(folder_matches) > 1:
        sys.stderr.write(
            f"error: {id_or_path!r} matches multiple folder-only sessions:\n"
        )
        for d in folder_matches:
            sys.stderr.write(f"  {d}\n")
        sys.exit(2)
    if len(folder_matches) == 1:
        folder = folder_matches[0]
        proj_dir = folder.parent
        sub_dir = folder / "subagents"
        subs = sorted(sub_dir.glob("*.jsonl")) if sub_dir.is_dir() else []
        idx = load_session_index(proj_dir, folder.name)
        if not subs and not idx:
            sys.exit(
                f"error: session {folder.name!r} exists but has no main transcript, "
                f"no subagents, and no index metadata — nothing to replay.\n"
                f"  folder: {folder}"
            )
        return SessionBundle(
            session_id=folder.name,
            main_path=None,
            subagent_paths=subs,
            folder=folder,
            project_slug=proj_dir.name,
            index_meta=idx,
        )

    # Last resort: UUID might only exist in sessions-index.json (no folder, no
    # jsonl — everything was cleaned up). Scan all project dirs.
    for proj_dir in sorted(SESSIONS_ROOT.iterdir()):
        if not proj_dir.is_dir():
            continue
        idx = load_session_index(proj_dir, id_or_path)
        if idx:
            return SessionBundle(
                session_id=id_or_path,
                main_path=None,
                subagent_paths=[],
                folder=None,
                project_slug=proj_dir.name,
                index_meta=idx,
            )

    sys.exit(f"error: no session matching {id_or_path!r} under {SESSIONS_ROOT}")


def truncate(s: str, n: int) -> str:
    s = s.strip()
    if len(s) <= n:
        return s
    return s[:n].rstrip() + f"… [+{len(s) - n} chars]"


def format_ts(ts: str) -> str:
    if not ts:
        return ""
    return ts.replace("T", " ")[:19]


def clean_user_text(text: str, verbatim: bool) -> str:
    if verbatim:
        return text
    text = NOISE_RE.sub("", text)
    text = COMMAND_NAME_RE.sub(r"_(invoked \1)_", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def normalize_user_text(s: str) -> str:
    """Key used to dedup history.jsonl prompts against main-transcript turns."""
    if not isinstance(s, str):
        return ""
    s = clean_user_text(s, verbatim=False)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s[:200]


def extract_user_tool_results(msg: dict) -> list[str]:
    content = msg.get("content")
    results: list[str] = []
    if not isinstance(content, list):
        return results
    for part in content:
        if not isinstance(part, dict) or part.get("type") != "tool_result":
            continue
        c = part.get("content")
        if isinstance(c, str):
            results.append(c)
        elif isinstance(c, list):
            for item in c:
                if isinstance(item, dict) and item.get("type") == "text":
                    results.append(item.get("text", ""))
    return results


def summarize_tool_use(part: dict) -> str:
    name = part.get("name", "?")
    inp = part.get("input") or {}
    priority = (
        "file_path", "path", "pattern", "command", "description",
        "prompt", "query", "url", "skill", "subagent_type",
        "input", "arguments", "cell_id",
    )
    hits: list[str] = []
    for k in priority:
        if k in inp:
            v = inp[k]
            if isinstance(v, (dict, list)):
                v = json.dumps(v, separators=(",", ":"))
            hits.append(f"{k}={truncate(str(v), 100)!r}")
    if not hits:
        hits = [f"{k}=…" for k in list(inp)[:3]]
    return f"{name}({', '.join(hits)})"


def extract_assistant_blocks(msg: dict) -> list[tuple[str, str]]:
    """(kind, body) tuples; kind in {text, thinking, tool_use}."""
    out: list[tuple[str, str]] = []
    for part in msg.get("content") or []:
        if not isinstance(part, dict):
            continue
        t = part.get("type")
        if t == "text":
            out.append(("text", part.get("text", "")))
        elif t == "thinking":
            out.append(("thinking", part.get("thinking", "")))
        elif t == "reasoning":  # Codex reasoning (usually encrypted)
            out.append(("reasoning", part.get("text", "")))
        elif t == "tool_use":
            out.append(("tool_use", summarize_tool_use(part)))
    return out


def load_jsonl_events(path: Path, source: str) -> list[dict]:
    events: list[dict] = []
    with path.open() as f:
        for raw in f:
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            obj["_source"] = source
            events.append(obj)
    return events


def ms_to_iso(ts_ms: int | float) -> str:
    whole = int(ts_ms)
    d = dt.datetime.fromtimestamp(whole / 1000, dt.timezone.utc)
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{whole % 1000:03d}Z"


def load_history_events(session_id: str) -> list[dict]:
    """Synthesize user events from ~/.claude/history.jsonl for this session."""
    if not HISTORY_PATH.is_file():
        return []
    events: list[dict] = []
    with HISTORY_PATH.open() as f:
        for raw in f:
            try:
                h = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if h.get("sessionId") != session_id:
                continue
            ts_ms = h.get("timestamp")
            if ts_ms is None:
                continue
            display = h.get("display") or ""
            if not display.strip():
                continue
            events.append({
                "type": "user",
                "timestamp": ms_to_iso(ts_ms),
                "sessionId": session_id,
                "cwd": h.get("project"),
                "message": {"role": "user", "content": display},
                "isSidechain": False,
                "_source": "history",
            })
    return events


# ---------------------------------------------------------------------------
# OpenAI Codex CLI rollout transcripts
#
# Codex stores sessions under ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl in a
# different shape than Claude Code. Every line is an envelope
# {timestamp, type, payload}; the conversational signal is spread across
# response_item and event_msg records. We convert those into the SAME
# Claude-shaped event dicts that render_event() consumes, so all rendering,
# flags, and --save-dir logic is reused unchanged.
# ---------------------------------------------------------------------------

CODEX_ENVELOPE_TYPES = {
    "session_meta", "response_item", "event_msg", "turn_context", "compacted",
}


def is_codex_file(path: Path) -> bool:
    """Detect a Codex rollout transcript (vs a Claude Code one) by its envelope.

    Codex wraps content as {timestamp, type, payload} with type in
    CODEX_ENVELOPE_TYPES. Claude Code puts the role in a top-level `type`
    (user/assistant/...) and carries a `message` key, never a `payload`.
    """
    try:
        with path.open() as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                obj = json.loads(raw)
                return (
                    isinstance(obj, dict)
                    and "payload" in obj
                    and obj.get("type") in CODEX_ENVELOPE_TYPES
                )
    except (OSError, json.JSONDecodeError):
        return False
    return False


def _codex_tool_input(payload: dict) -> dict:
    """Normalize a Codex tool-call payload into a Claude-style `input` dict so
    summarize_tool_use() can render a one-liner."""
    if payload.get("type") == "function_call":
        raw = payload.get("arguments")
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {"arguments": raw}
            return parsed if isinstance(parsed, dict) else {"arguments": raw}
        return raw if isinstance(raw, dict) else {}
    # custom_tool_call: `input` is usually a raw string (often a code snippet).
    inp = payload.get("input")
    if isinstance(inp, dict):
        return inp
    return {"input": inp if isinstance(inp, str) else ""}


def _codex_output_text(output) -> str:
    """Flatten a Codex tool-call output (string, or list of {type,text}) to text."""
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        parts = []
        for item in output:
            if isinstance(item, dict):
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(p for p in parts if p)
    return ""


def resolve_codex_path(id_or_path: str) -> Path | None:
    """Resolve the user's argument to a Codex rollout file, or None to defer to
    the Claude resolver.

    Accepts an absolute path to a Codex .jsonl, or a UUID / prefix. Codex names
    files rollout-<timestamp>-<uuid>.jsonl under ~/.codex/sessions/YYYY/MM/DD/,
    so a bare UUID is matched as a filename substring. To keep Claude UUIDs and
    Codex UUIDs from colliding, a bare id is only claimed for Codex when the
    Claude tree has no matching .jsonl. Exits (code 2) on an ambiguous prefix.
    """
    p = Path(id_or_path).expanduser()
    if p.is_file():
        return p if is_codex_file(p) else None
    if p.exists():
        return None  # a dir or non-codex path — let the Claude resolver handle it
    if not CODEX_SESSIONS_ROOT.is_dir():
        return None
    # Bare id/prefix: don't poach an id the Claude tree already owns.
    claude_hits = (
        sorted(SESSIONS_ROOT.glob(f"*/{id_or_path}*.jsonl"))
        if SESSIONS_ROOT.is_dir() else []
    )
    if claude_hits:
        return None
    matches = sorted(CODEX_SESSIONS_ROOT.glob(f"**/*{id_or_path}*.jsonl"))
    if len(matches) > 1:
        sys.stderr.write(f"error: {id_or_path!r} matches multiple Codex sessions:\n")
        for m in matches:
            sys.stderr.write(f"  {m}\n")
        sys.exit(2)
    return matches[0] if matches else None


def load_codex_events(path: Path) -> tuple[list[dict], dict]:
    """Convert a Codex rollout transcript into Claude-shaped event dicts.

    Returns (events, meta); meta carries session_id/cwd/model/cli_version from the
    session_meta record. Only conversational signal is kept:

        event_msg/user_message                -> user text turn
        response_item/message role=assistant  -> assistant text turn
        response_item/function_call           -> assistant tool_use   (--tools)
        response_item/custom_tool_call        -> assistant tool_use   (--tools)
        response_item/function_call_output    -> user tool_result     (--tool-results)
        response_item/custom_tool_call_output -> user tool_result     (--tool-results)

    Dropped as noise/duplication: response_item/message role in {user,developer}
    (harness-injected AGENTS.md/environment context and the system prompt),
    response_item/reasoning (encrypted_content with no plaintext summary),
    event_msg/agent_message (byte-identical to the assistant response_item), and
    bookkeeping (token_count, task_started/complete, *_tool_call_end echoes).
    """
    events: list[dict] = []
    meta: dict = {}

    def emit(etype: str, ts: str, content) -> None:
        events.append({
            "type": etype,
            "timestamp": ts,
            "message": {"role": etype, "content": content},
            "isSidechain": False,
            "_source": "main",
        })

    with path.open() as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            ts = obj.get("timestamp", "")
            etype = obj.get("type")
            payload = obj.get("payload")
            if not isinstance(payload, dict):
                continue

            if etype == "session_meta":
                meta.setdefault("session_id",
                                payload.get("session_id") or payload.get("id"))
                meta.setdefault("cwd", payload.get("cwd"))
                meta.setdefault("model",
                                payload.get("model") or payload.get("model_provider"))
                meta.setdefault("cli_version", payload.get("cli_version"))
                continue

            if etype == "event_msg":
                # The clean, user-typed prompt. (All other event_msg subtypes are
                # duplicates of response_items or bookkeeping — skip them.)
                if payload.get("type") == "user_message":
                    text = payload.get("message") or ""
                    imgs = payload.get("images") or payload.get("local_images") or []
                    if imgs:
                        note = f"[{len(imgs)} image(s) attached]"
                        text = note if not text.strip() else f"{text}\n\n{note}"
                    if text.strip():
                        emit("user", ts, text)
                continue

            if etype == "response_item":
                pt = payload.get("type")
                if pt == "message":
                    if payload.get("role") != "assistant":
                        continue  # user/developer = injected context / system
                    text = "".join(
                        b.get("text", "") for b in payload.get("content", [])
                        if isinstance(b, dict)
                    )
                    if text.strip():
                        emit("assistant", ts, [{"type": "text", "text": text}])
                elif pt in ("function_call", "custom_tool_call"):
                    emit("assistant", ts, [{
                        "type": "tool_use",
                        "name": payload.get("name", "?"),
                        "input": _codex_tool_input(payload),
                    }])
                elif pt in ("function_call_output", "custom_tool_call_output"):
                    text = _codex_output_text(payload.get("output"))
                    if text.strip():
                        emit("user", ts, [{"type": "tool_result", "content": text}])
                elif pt == "reasoning":
                    # Codex usually stores reasoning as encrypted_content with an
                    # empty `summary`; keep a block so --thinking surfaces a
                    # placeholder, and render the summary text on the rare
                    # occasions it is present in plaintext.
                    summary = payload.get("summary") or []
                    text = "\n".join(
                        s.get("text", "") for s in summary if isinstance(s, dict)
                    ).strip()
                    emit("assistant", ts, [{"type": "reasoning", "text": text}])
                continue

    return events, meta


def source_tag(source: str) -> str:
    if source == "main" or not source:
        return ""
    if source == "history":
        return " [from history.jsonl]"
    if source.startswith("subagent:"):
        return f" [sub: {source.split(':', 1)[1]}]"
    return f" [{source}]"


def derive_flag_tokens(args: argparse.Namespace) -> list[str]:
    """Filename tokens describing the view flags, in a canonical (stable) order.

    Built from the flags exactly as passed — call this BEFORE --full is expanded
    into its component flags and BEFORE history auto-enable mutates args.history,
    so the name mirrors the command the user typed (e.g. `--full` -> "full", not
    the four flags it expands to). The fixed ordering here means the same logical
    replay always maps to one filename regardless of how the flags were ordered
    on the command line.
    """
    tokens: list[str] = []
    if args.verbatim:
        tokens.append("verbatim")
    if args.raw:
        tokens.append("raw")
    if args.full:
        tokens.append("full")
    else:
        if args.tools:
            tokens.append("tools")
        if args.tool_results:
            tokens.append("tool-results")
        if args.thinking:
            tokens.append("thinking")
        if args.sidechains:
            tokens.append("sidechains")
    if args.embed_images:
        tokens.append("embed-images")
    if args.history is True:        # explicit --history (None = unspecified)
        tokens.append("history")
    elif args.history is False:     # explicit --no-history
        tokens.append("no-history")
    if args.max_chars != 400:       # only when overriding the default
        tokens.append(f"max{args.max_chars}")
    return tokens


def derive_output_path(save_dir: Path, session_id: str | None,
                       tokens: list[str]) -> Path:
    """Build `replay-<shortid>[-<flag>...].md` under save_dir, never clobbering
    an existing file — append -2, -3, ... until the name is free."""
    short = (session_id or "session")[:8]
    base = "-".join(["replay", short, *tokens])
    candidate = save_dir / f"{base}.md"
    n = 2
    while candidate.exists():
        candidate = save_dir / f"{base}-{n}.md"
        n += 1
    return candidate


def render_event(obj: dict, args: argparse.Namespace, chunks: list[str]) -> int:
    """Render one event; append to chunks. Returns turns added (0 or 1)."""
    t = obj.get("type")
    if t not in ("user", "assistant"):
        return 0
    sidechain = bool(obj.get("isSidechain"))
    if sidechain and not args.sidechains:
        return 0

    ts = format_ts(obj.get("timestamp", ""))
    source = obj.get("_source", "main")
    msg = obj.get("message") or {}
    tag_suffix = (" [sidechain]" if sidechain else "") + source_tag(source)

    def header(who: str) -> str:
        if args.raw:
            return f"\n[{who.upper()} {ts}{tag_suffix}]\n"
        return f"\n### {who} · {ts}{tag_suffix}\n"

    if t == "user":
        content = msg.get("content")
        # isMeta user events are harness-injected synthetic messages (command-body
        # expansions, "[Image: source: ...]" refs) — noise for a conversation
        # replay. Keep them only in verbatim mode.
        if obj.get("isMeta") and not args.verbatim:
            return 0
        if isinstance(content, str):
            text = clean_user_text(content, args.verbatim)
            if text:
                chunks.append(header("user"))
                chunks.append(f"\n{text}\n")
                return 1
            return 0
        if isinstance(content, list):
            counted = 0
            header_written = False

            # A prompt carrying an image/attachment stores its text in a list of
            # blocks rather than a bare string. Render the text blocks too, or the
            # whole prompt is silently dropped.
            parts = [b.get("text", "") for b in content
                     if isinstance(b, dict) and b.get("type") == "text"]
            text = clean_user_text("\n".join(p for p in parts if p), args.verbatim)
            if text:
                chunks.append(header("user"))
                header_written = True
                counted = 1
                chunks.append(f"\n{text}\n")

            # Image blocks: by default emit a lean `[Image #N: <media_type>]`
            # placeholder. Full base64 embedding (an inline `data:` URI that
            # renders the picture directly in the markdown) is opt-in via
            # --embed-images, and never applied in --raw plain-text output since
            # a multi-hundred-KB URI would swamp it. The pixels live as base64
            # in the transcript (the image-cache PNG the harness references is
            # ephemeral and often already deleted), so embedding inlines that.
            # imagePasteIds aligns the label with the "[Image #N]" marker the
            # harness leaves in the prompt text.
            paste_ids = obj.get("imagePasteIds") or []
            img_n = 0
            for b in content:
                if not isinstance(b, dict) or b.get("type") != "image":
                    continue
                src = b.get("source") or {}
                label = paste_ids[img_n] if img_n < len(paste_ids) else img_n + 1
                img_n += 1
                if not header_written:
                    chunks.append(header("user"))
                    header_written = True
                    counted = 1
                media = src.get("media_type", "image")
                uri = None
                if args.embed_images and not args.raw:
                    if src.get("type") == "base64" and src.get("data"):
                        uri = f"data:{media};base64,{src['data']}"
                    elif src.get("type") == "url" and src.get("url"):
                        uri = src["url"]
                if uri is not None:
                    chunks.append(f"\n![Image #{label}]({uri})\n")
                else:
                    chunks.append(f"\n[Image #{label}: {media}]\n")

            if args.tool_results:
                for tr in extract_user_tool_results(msg):
                    chunks.append(header("tool_result"))
                    chunks.append(f"\n```\n{truncate(tr, args.max_chars)}\n```\n")
            return counted
        return 0

    # assistant
    blocks = extract_assistant_blocks(msg)
    wrote_header = False
    counted = 0
    for kind, body in blocks:
        if kind == "text" and body.strip():
            if not wrote_header:
                chunks.append(header("assistant"))
                wrote_header = True
                counted = 1
            chunks.append(f"\n{body.strip()}\n")
        elif kind == "thinking" and args.thinking and body.strip():
            if not wrote_header:
                chunks.append(header("assistant"))
                wrote_header = True
            chunks.append(f"\n> _thinking:_ {truncate(body, args.max_chars)}\n")
        elif kind == "reasoning" and args.thinking:
            if not wrote_header:
                chunks.append(header("assistant"))
                wrote_header = True
            shown = truncate(body, args.max_chars) if body.strip() \
                else "[encrypted by Codex]"
            chunks.append(f"\n> _reasoning:_ {shown}\n")
        elif kind == "tool_use" and args.tools:
            if not wrote_header:
                chunks.append(header("assistant"))
                wrote_header = True
            chunks.append(f"\n- **→** `{body}`\n")
    return counted


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("session", help="session UUID, prefix, or path to .jsonl/folder")
    ap.add_argument("--tools", action="store_true",
                    help="include tool call summaries")
    ap.add_argument("--tool-results", action="store_true", dest="tool_results",
                    help="include (truncated) tool results")
    ap.add_argument("--thinking", action="store_true",
                    help="include assistant thinking blocks")
    ap.add_argument("--sidechains", action="store_true",
                    help="include subagent sidechain turns")
    ap.add_argument("--history", dest="history", action="store_true", default=None,
                    help="interleave user prompts from ~/.claude/history.jsonl "
                         "(auto-enabled for folder-only sessions)")
    ap.add_argument("--no-history", dest="history", action="store_false",
                    help="disable history.jsonl backfill (overrides auto-enable)")
    ap.add_argument("--full", action="store_true",
                    help="shortcut for --tools --tool-results --thinking --sidechains")
    ap.add_argument("--max-chars", type=int, default=400, dest="max_chars",
                    help="truncate tool results / thinking above this (default 400)")
    ap.add_argument("--verbatim", action="store_true",
                    help="keep <system-reminder> and similar harness tags")
    ap.add_argument("--raw", action="store_true",
                    help="plain text output, no markdown headers")
    ap.add_argument("--embed-images", dest="embed_images", action="store_true",
                    help="embed images inline as base64 data: URIs so they "
                         "render in the markdown (default: a lean "
                         "[Image #N: <media_type>] placeholder); ignored in --raw")
    ap.add_argument("--save-dir", dest="save_dir", default=None,
                    help="write output to a flag-derived, non-clobbering file "
                         "in this directory (created if missing) instead of "
                         "stdout; prints the saved path")
    args = ap.parse_args()

    # Capture filename tokens from the flags AS TYPED, before --full expansion
    # and history auto-enable change the resolved flag state.
    flag_tokens = derive_flag_tokens(args)

    if args.full:
        args.tools = args.tool_results = args.thinking = args.sidechains = True

    # Codex rollout transcripts live outside ~/.claude and use a different
    # envelope. Accept either a direct path or a Codex UUID/prefix (matched
    # against ~/.codex/sessions/**/rollout-*.jsonl), then convert to the same
    # internal event shape Claude sessions produce.
    history_added = 0
    cwd: str | None = None
    codex_path = resolve_codex_path(args.session)
    if codex_path is not None:
        events, codex_meta = load_codex_events(codex_path)
        session_id = codex_meta.get("session_id") or codex_path.stem
        cwd = codex_meta.get("cwd")
        bundle = SessionBundle(
            session_id=session_id,
            main_path=codex_path,
            is_codex=True,
            codex_meta=codex_meta,
        )
        args.history = False  # no Codex equivalent of ~/.claude/history.jsonl
    else:
        bundle = resolve_session(args.session)

        # Subagent content is 100% sidechain. If that's all we have, the
        # --sidechains flag would otherwise be a footgun.
        if bundle.is_folder_only or bundle.subagent_paths and not bundle.main_path:
            args.sidechains = True

        # history.jsonl auto-default: on for folder-only, off otherwise.
        if args.history is None:
            args.history = bundle.is_folder_only

        events = []
        if bundle.main_path:
            events.extend(load_jsonl_events(bundle.main_path, "main"))
        for sp in bundle.subagent_paths:
            events.extend(load_jsonl_events(sp, f"subagent:{sp.stem}"))

        # Session ID may be unknown when given a raw subagent path — sniff it.
        session_id = bundle.session_id
        if not session_id:
            for obj in events:
                sid = obj.get("sessionId")
                if sid:
                    session_id = sid
                    break

        if args.history and session_id:
            hist = load_history_events(session_id)
            if bundle.main_path and hist:
                seen: set[str] = set()
                for obj in events:
                    if obj.get("type") != "user" or obj.get("_source") != "main":
                        continue
                    c = obj.get("message", {}).get("content")
                    if isinstance(c, str):
                        key = normalize_user_text(c)
                        if key:
                            seen.add(key)
                hist = [h for h in hist
                        if normalize_user_text(h["message"]["content"]) not in seen]
            events.extend(hist)
            history_added = len(hist)

    # ISO-8601 strings sort lexically; history ms-epoch was formatted to match.
    events.sort(key=lambda o: o.get("timestamp", ""))

    if cwd is None:
        for obj in events:
            c = obj.get("cwd")
            if c:
                cwd = c
                break

    chunks: list[str] = []
    turns = 0
    for obj in events:
        turns += render_event(obj, args, chunks)

    out = io.StringIO()
    idx = bundle.index_meta
    if not args.raw:
        out.write(f"# Session replay: `{session_id or bundle.session_id or '?'}`\n\n")
        if bundle.is_codex:
            cm = bundle.codex_meta
            ver = cm.get("cli_version")
            out.write(
                "- **format**: OpenAI Codex CLI rollout"
                + (f" (v{ver})" if ver else "") + "\n"
            )
            if cm.get("model"):
                out.write(f"- **model**: {cm['model']}\n")
        if idx and idx.summary:
            out.write(f"- **summary**: {idx.summary}\n")
        if bundle.main_path:
            out.write(f"- **main**: `{bundle.main_path}`\n")
        else:
            out.write(
                "- **main**: _(none — folder-only session; main transcript was "
                "not retained)_\n"
            )
        if bundle.subagent_paths:
            out.write(
                f"- **subagents**: {len(bundle.subagent_paths)} file(s)"
                + (f" in `{bundle.folder}/subagents/`" if bundle.folder else "")
                + "\n"
            )
        if args.history:
            out.write(
                f"- **history.jsonl**: {history_added} user prompt(s) interleaved\n"
            )
        if cwd:
            out.write(f"- **cwd**: `{cwd}`\n")
        if idx:
            if idx.created:
                out.write(f"- **created**: {format_ts(idx.created)}\n")
            if idx.git_branch:
                out.write(f"- **branch**: {idx.git_branch}\n")
            if idx.message_count:
                out.write(f"- **original messages**: {idx.message_count}\n")
        out.write(f"- **turns**: {turns}\n")
        flags = ", ".join(
            f"{name}={'on' if getattr(args, name) else 'off'}"
            for name in ("tools", "tool_results", "thinking", "sidechains", "history")
        )
        out.write(f"- **filters**: {flags}\n\n---\n")
    out.write("".join(chunks).rstrip() + "\n")
    report = out.getvalue()

    if args.save_dir:
        save_dir = Path(args.save_dir).expanduser()
        save_dir.mkdir(parents=True, exist_ok=True)
        path = derive_output_path(save_dir, session_id or bundle.session_id,
                                  flag_tokens)
        path.write_text(report)
        line_count = report.count("\n")
        print(f"saved: {path}  ({turns} turns, {line_count} lines)")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
