#!/usr/bin/env python3
"""Inject overclock's working rules once per session (cache-friendly: never changes mid-session)."""
import json

RULES = """overclock efficiency rules (quality first):
- Lead with the answer; no preamble or recap. Keep code, paths, numbers and errors exact.
- Send independent tool calls together in one message. Search before opening files; read only the line ranges you need; don't re-read unchanged files.
- Run commands as-is (no head/tail): overclock trims long output, keeping start, end and all error lines, plus a path to the full text.
- For searches needing many reads, use the overclock:scout subagent.
- At a natural break in a long task, suggest /overclock:handoff to continue in a fresh session."""

import os
if os.environ.get("OVERCLOCK_RULES") == "off":
    raise SystemExit(0)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": RULES}}))
