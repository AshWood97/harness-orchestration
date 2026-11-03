"""Optional ZCode user hook: save metadata observations for a bound session.

The hook never issues decisions, reads the transcript, or changes task status.
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.orchestration import Coordinator  # noqa: E402

EVENTS = {"SessionStart", "UserPromptSubmit", "PreToolUse", "PermissionRequest",
          "PostToolUse", "PostToolUseFailure", "Stop"}


def observe(database, event):
    if not os.path.isfile(database):
        return False
    session = event.get("session_id") or event.get("sessionId")
    kind = event.get("hook_event_name") or event.get("hookEventName")
    if not session or kind not in EVENTS:
        return False
    coordinator = Coordinator(database)
    binding = coordinator.task_for_session(session, "zcode_desktop")
    if not binding:
        return False
    call_id = event.get("tool_use_id") or event.get("toolUseId")
    event_id = f"{kind}:{call_id}" if call_id else None
    payload = {"session_id": session, "cwd": event.get("cwd"),
               "tool_name": event.get("tool_name") or event.get("toolName"),
               "tool_use_id": call_id}
    return coordinator.record_event(binding["task_id"], binding["attempt"],
                                    "zcode_hook", event_id, kind, payload)


def main():
    # Empty stdout means no decision or extra context. Observation errors must
    # not prevent an unrelated ZCode session from continuing.
    try:
        observe(sys.argv[1], json.loads(sys.stdin.readline()))
    except (IndexError, ValueError, OSError, sqlite3.Error):
        pass


if __name__ == "__main__":
    main()
