#!/usr/bin/env python3
"""Persist exact Codex session timestamps and inject them into agent context."""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SAFE_FILENAME = re.compile(r"[^A-Za-z0-9_.-]+")


def timestamp_now() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %I:%M %p %Z")


def read_payload() -> dict[str, Any]:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"session-tools: invalid SessionStart payload: {exc}") from exc

    if not isinstance(payload, dict):
        raise SystemExit("session-tools: SessionStart payload must be a JSON object")
    return payload


def state_path(plugin_data: Path, session_id: str) -> Path:
    safe_id = SAFE_FILENAME.sub("_", session_id).strip("._")
    if not safe_id:
        raise SystemExit("session-tools: SessionStart payload has an invalid session_id")
    return plugin_data / "session-summary" / f"{safe_id}.json"


def load_state(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_path, path)


def update_state(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    session_id = str(payload.get("session_id") or "")
    source = str(payload.get("source") or "startup")
    now = timestamp_now()

    if source in {"startup", "clear"}:
        state: dict[str, Any] = {
            "session_id": session_id,
            "start_time": now,
            "resume_times": [],
        }
    else:
        state = load_state(path)
        state["session_id"] = session_id
        state.setdefault("start_time", "")
        resume_times = state.get("resume_times")
        if not isinstance(resume_times, list):
            resume_times = []
        state["resume_times"] = resume_times
        if source == "resume":
            resume_times.append(now)

    state["cwd"] = str(payload.get("cwd") or "")
    write_state(path, state)
    return state


def emit_context(state: dict[str, Any]) -> None:
    metadata = {
        "session_id": state.get("session_id", ""),
        "start_time": state.get("start_time", ""),
        "resume_times": state.get("resume_times", []),
    }
    additional_context = (
        "SESSION_SUMMARY_METADATA (authoritative; do not estimate missing values):\n"
        + json.dumps(metadata, sort_keys=True)
    )
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        }
    }
    json.dump(output, sys.stdout)
    sys.stdout.write("\n")


def main() -> None:
    payload = read_payload()
    session_id = str(payload.get("session_id") or "")
    if not session_id:
        raise SystemExit("session-tools: SessionStart payload is missing session_id")

    plugin_data_value = os.environ.get("PLUGIN_DATA", "")
    if not plugin_data_value:
        raise SystemExit("session-tools: PLUGIN_DATA is unavailable")

    path = state_path(Path(plugin_data_value), session_id)
    state = update_state(payload, path)
    emit_context(state)


if __name__ == "__main__":
    main()
