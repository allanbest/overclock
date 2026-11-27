#!/usr/bin/env python3
"""Guide the compaction summary: keep what's needed to continue, drop what's been used up."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from session_start import find_active_project  # noqa: E402

BASE_GUIDE = (
    "When summarizing, keep: the user's goal and constraints; decisions made and why; "
    "exact file paths, names, commands and identifiers in play; errors or failing tests still "
    "unresolved (verbatim); what's done vs. still to do. Drop: raw tool output that was already "
    "acted on, exploration dead ends, superseded plans, and conversational filler. "
    "Be compact: bullet points, no prose."
)


def main():
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except ValueError:
        event = {}

    out = [BASE_GUIDE]
    if os.environ.get("OVERCLOCK_DEEPWORK") != "off":
        try:
            found = find_active_project(event.get("cwd"))
        except Exception:
            found = None
        if found:
            _, slug, proj_dir, _, text = found
            m = re.search(r"^Mode:\s*([a-zA-Z0-9_-]+)", text, flags=re.MULTILINE)
            mode = m.group(1).strip().lower() if m else "unknown"
            out.append(
                f"Also preserve the active overclock Deepwork project '{slug}' ({mode} mode) at {proj_dir}: "
                f"current hypothesis/task ID, logged dead ends not to retry, and unresolved test/experiment failures."
            )
    print("\n".join(out))


if __name__ == "__main__":
    main()
