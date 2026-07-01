#!/usr/bin/env python3
"""Merge N Claude Code session transcripts into one timestamp-sorted replay.

Where extract-session.py renders a single session, this renders several at once:
every event from every named session is pooled, sorted by timestamp, and
rendered in true chronological order. Each turn header is badged with its
origin session, so interleaved/tandem sessions (e.g. the user relaying
responses between two parallel agents) read as a single coherent timeline.

Usage:
    merge-sessions.py <id-or-path> <id-or-path> [<id-or-path> ...] [flags]

Each positional argument is resolved exactly like extract-session.py's first
argument: a full UUID, a prefix (>=4 chars), an absolute path to a .jsonl, or a
session folder. At least two are required.

Flags mirror extract-session.py:
    --tools --tool-results --thinking --sidechains --full
    --max-chars N --verbatim --raw --embed-images --save-dir DIR
Plus:
    --models   annotate each assistant turn's badge with the model that
               produced it (reveals mid-session model switches and
               cross-session model differences)

Sessions may be Claude Code transcripts or OpenAI Codex rollouts, in any mix —
each positional argument is detected exactly as extract-session.py does, so a
Codex UUID/path and a Claude UUID/path can be pooled into one timeline.

This script is read-only; it never modifies the original transcripts. It
imports extract-session.py as a sibling module to stay in lock-step with its
rendering and resolution logic.
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_EXTRACTOR = _HERE / "extract-session.py"

if not _EXTRACTOR.is_file():
    sys.exit(f"error: cannot find extract-session.py next to {__file__}")

_spec = importlib.util.spec_from_file_location("extract_session", _EXTRACTOR)
ex = importlib.util.module_from_spec(_spec)
sys.modules["extract_session"] = ex  # dataclasses need the module registered
_spec.loader.exec_module(ex)


def short(session_id: str | None) -> str:
    """First 8 chars of a UUID-ish id, or '?' when unknown."""
    if not session_id:
        return "?"
    return session_id[:8]


def badge_for(index: int, session_id: str | None) -> str:
    """A·<short8>, B·<short8>, … then fall back to bare short id past Z."""
    if index < 26:
        return f"{chr(ord('A') + index)}·{short(session_id)}"
    return short(session_id)


def build_args(ns: argparse.Namespace) -> argparse.Namespace:
    full = ns.full
    return argparse.Namespace(
        tools=ns.tools or full,
        tool_results=ns.tool_results or full,
        thinking=ns.thinking or full,
        sidechains=ns.sidechains or full,
        history=False,
        full=full,
        max_chars=ns.max_chars,
        verbatim=ns.verbatim,
        raw=ns.raw,
        # render_event reads args.embed_images directly when it hits an image
        # block, so this MUST be present or merging any session with an image
        # prompt raises AttributeError.
        embed_images=ns.embed_images,
    )


def derive_merge_output_path(save_dir: Path, shorts: list[str],
                             tokens: list[str]) -> Path:
    """Build `replay-merge-<shortA>-<shortB>[…][-<flag>...].md` under save_dir,
    never clobbering an existing file — append -2, -3, ... until the name is
    free. Mirrors extract-session.py's derive_output_path naming scheme (the
    single-session helper hardcodes a `replay-<id>` stem, so we can't call it
    directly, but the flag tokens and non-clobber suffixing are identical)."""
    stem = "-".join(["replay-merge", *shorts, *tokens])
    candidate = save_dir / f"{stem}.md"
    n = 2
    while candidate.exists():
        candidate = save_dir / f"{stem}-{n}.md"
        n += 1
    return candidate


def load_session_events(arg: str, label: str, want_sidechains: bool):
    """Resolve one session arg and return (events, bundle, session_id), tagged
    with `label`. Handles both Claude Code sessions and OpenAI Codex rollouts:
    a Codex UUID/path is detected exactly as extract-session.py's main() does
    (resolve_codex_path → load_codex_events), so a merge can pool Codex and
    Claude sessions in one timeline. Codex rollouts have no subagent sidechains,
    so want_sidechains simply doesn't apply to them."""
    codex_path = ex.resolve_codex_path(arg)  # exits on ambiguous Codex prefix
    if codex_path is not None:
        events, codex_meta = ex.load_codex_events(codex_path)
        sid = codex_meta.get("session_id") or codex_path.stem
        bundle = ex.SessionBundle(
            session_id=sid,
            main_path=codex_path,
            is_codex=True,
            codex_meta=codex_meta,
        )
    else:
        bundle = ex.resolve_session(arg)  # exits the process on hard errors
        events = []
        if bundle.main_path:
            events.extend(ex.load_jsonl_events(bundle.main_path, "main"))
        if want_sidechains:
            for sp in bundle.subagent_paths:
                events.extend(ex.load_jsonl_events(sp, f"subagent:{sp.stem}"))
        sid = bundle.session_id or next(
            (e.get("sessionId") for e in events if e.get("sessionId")), None
        )
    for e in events:
        e["_label"] = label
        e["_session_id"] = sid
    return events, bundle, sid


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("sessions", nargs="+", help="two or more session UUIDs/prefixes/paths")
    ap.add_argument("--tools", action="store_true")
    ap.add_argument("--tool-results", action="store_true", dest="tool_results")
    ap.add_argument("--thinking", action="store_true")
    ap.add_argument("--sidechains", action="store_true")
    ap.add_argument("--full", action="store_true",
                    help="shortcut for --tools --tool-results --thinking --sidechains")
    ap.add_argument("--max-chars", type=int, default=400, dest="max_chars")
    ap.add_argument("--verbatim", action="store_true")
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--embed-images", dest="embed_images", action="store_true",
                    help="embed images inline as base64 data: URIs so they "
                         "render in the markdown (default: a lean placeholder); "
                         "ignored in --raw")
    ap.add_argument("--save-dir", dest="save_dir", default=None,
                    help="write output to a flag-derived, non-clobbering file "
                         "in this directory (created if missing) instead of "
                         "stdout; prints the saved path")
    ap.add_argument("--models", action="store_true",
                    help="annotate each assistant turn's badge with its model")
    cli = ap.parse_args()

    if len(cli.sessions) < 2:
        ap.error("merge needs at least two sessions; for one use extract-session.py")

    # Filename tokens from the flags AS TYPED, before --full is expanded. Merge
    # has no history concept, so blank out the attribute derive_flag_tokens
    # inspects (else it would stamp "no-history" into every merged filename);
    # --models is merge-only, so append its token ourselves.
    cli.history = None
    flag_tokens = ex.derive_flag_tokens(cli)
    if cli.models:
        flag_tokens.append("models")

    args = build_args(cli)
    want_sidechains = args.sidechains

    # Resolve + load every session, assigning a stable badge by input order.
    events: list[dict] = []
    meta: list[tuple[str, object, str | None]] = []  # (label, bundle, session_id)
    for i, arg in enumerate(cli.sessions):
        evs, bundle, sid = load_session_events(arg, badge_for(i, None), want_sidechains)
        # Re-badge now that we know the real session id.
        label = badge_for(i, sid)
        for e in evs:
            e["_label"] = label
        events.extend(evs)
        meta.append((label, bundle, sid))

    # Same lexical ISO-8601 sort extract-session.py uses internally.
    events.sort(key=lambda o: o.get("timestamp", ""))

    # Neutralize the per-event "[main]" source tag; we splice our own badge in.
    ex.source_tag = lambda source: ""  # noqa: E731

    cwds = []
    for o in events:
        c = o.get("cwd")
        if c and c not in cwds:
            cwds.append(c)

    chunks: list[str] = []
    turns = 0
    rendered: dict[str, int] = {}
    for obj in events:
        before = len(chunks)
        added = ex.render_event(obj, args, chunks)
        label = obj.get("_label", "?")
        suffix = f"`{label}`"
        if cli.models and obj.get("type") == "assistant":
            model = (obj.get("message") or {}).get("model")
            if model:
                suffix = f"`{label}` · `{model}`"
        # Splice the badge into the first header chunk this event produced.
        for i in range(before, len(chunks)):
            c = chunks[i]
            if c.startswith("\n### "):
                chunks[i] = c.rstrip("\n") + f"  ·  {suffix}\n"
                break
        if added:
            rendered[label] = rendered.get(label, 0) + added
            turns += added

    out = io.StringIO()
    if not args.raw:
        ids = " ⇄ ".join(f"`{short(sid)}`" for _, _, sid in meta)
        out.write(f"# Merged session replay: {ids} (timestamp-sorted)\n\n")
        out.write(
            f"{len(meta)} sessions pooled and interleaved in true chronological "
            "order; each turn header is badged with its origin session"
            + (" and model" if cli.models else "") + ".\n\n"
        )
        for label, bundle, sid in meta:
            path = bundle.main_path or (
                f"{bundle.folder}/subagents/" if bundle.folder else "(unresolved)"
            )
            fmt = ""
            if getattr(bundle, "is_codex", False):
                ver = bundle.codex_meta.get("cli_version")
                fmt = " · _Codex" + (f" v{ver}" if ver else "") + "_"
            out.write(f"- **{label}**: `{path}` — {rendered.get(label, 0)} "
                      f"rendered turns{fmt}\n")
        if cwds:
            if len(cwds) == 1:
                out.write(f"- **cwd**: `{cwds[0]}`\n")
            else:
                out.write(f"- **cwds**: {', '.join(f'`{c}`' for c in cwds)}\n")
        out.write(f"- **merged turns**: {turns}\n")
        flags = ", ".join(
            f"{n}={'on' if getattr(args, n) else 'off'}"
            for n in ("tools", "tool_results", "thinking", "sidechains")
        )
        out.write(f"- **filters**: {flags}, verbatim={'on' if args.verbatim else 'off'}"
                  f", models={'on' if cli.models else 'off'}\n\n---\n")
    out.write("".join(chunks).rstrip() + "\n")
    report = out.getvalue()

    if cli.save_dir:
        save_dir = Path(cli.save_dir).expanduser()
        save_dir.mkdir(parents=True, exist_ok=True)
        shorts = [short(sid) for _, _, sid in meta]
        path = derive_merge_output_path(save_dir, shorts, flag_tokens)
        path.write_text(report)
        line_count = report.count("\n")
        print(f"saved: {path}  ({turns} turns, {line_count} lines)")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
