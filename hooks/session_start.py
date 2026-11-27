#!/usr/bin/env python3
"""overclock SessionStart: dual-platform startup context for Claude Code and Antigravity.

On Claude Code:
  - Adds the lean efficiency rules once at session start (unless OVERCLOCK_RULES=off).
  - Loads the latest raw transcript checkpoint on startup/clear (unless OVERCLOCK_RESUME=off).
  - Loads the active Deepwork project's state.md on startup/clear/compact (skipped on resume).

On Antigravity:
  - Stays 100% silent (`{}`) unless `.overclock/active` points to an active Deepwork project.
  - When active, injects a factual `systemMessage` with state.md and the mode playbook path.

Settings:
  OVERCLOCK_RULES=off        don't add Claude lean rules
  OVERCLOCK_RESUME=off       don't load transcript checkpoints
  OVERCLOCK_RESUME_DAYS=7    ignore checkpoints older than this
  OVERCLOCK_DEEPWORK=off     don't auto-load active Deepwork project state
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from checkpoint import project_dir, sid8  # noqa: E402

RULES = """overclock efficiency rules (quality first):
- Lead with the answer; no preamble or recap. Keep code, paths, numbers and errors exact.
- Send independent tool calls together in one message. Search before opening files; read only the line ranges you need; don't re-read unchanged files.
- Run commands as-is (no head/tail): overclock trims long output, keeping start, end and all error lines, plus a path to the full text.
- For searches needing many reads, use the overclock:scout subagent (model per the tier below).
- At a natural break in a long task, suggest /overclock:handoff to continue in a fresh session."""

MAX_CHARS = 2500
DEEPWORK_STATE_CAP = 2200
CLAUDE_TOTAL_CAP = 9000
PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ago(seconds):
    if seconds < 3600:
        return f"{seconds / 60:.0f} minutes ago"
    if seconds < 172800:
        return f"{seconds / 3600:.0f} hours ago"
    return f"{seconds / 86400:.0f} days ago"


def is_antigravity(event: dict) -> bool:
    return any(k in event for k in ("workspacePaths", "conversationId", "hookEventName", "artifactDirectoryPath"))


def find_active_project(start_dir: str):
    """Walk upward from start_dir for .overclock/active and return (root, slug, proj_dir, state_text) if active."""
    if not start_dir:
        return None
    cur = os.path.abspath(start_dir)
    while True:
        active_file = os.path.join(cur, ".overclock", "active")
        if os.path.isfile(active_file):
            try:
                slug = open(active_file, encoding="utf-8").read().strip()
            except OSError:
                return None
            if not slug or "/" in slug or "\\" in slug or ".." in slug or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
                return None
            proj_dir = os.path.join(cur, ".overclock", "projects", slug)
            state_path = os.path.join(proj_dir, "state.md")
            if not os.path.isfile(state_path):
                return None
            try:
                text = open(state_path, encoding="utf-8").read()
            except OSError:
                return None
            m = re.search(r"^Status:\s*(.+)$", text, flags=re.MULTILINE)
            status = (m.group(1).strip().lower() if m else "")
            if status != "active":
                return None
            return cur, slug, proj_dir, state_path, text
        if os.path.exists(os.path.join(cur, ".git")):
            return None
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def active_project_context(start_dir: str):
    if os.environ.get("OVERCLOCK_DEEPWORK") == "off":
        return None
    found = find_active_project(start_dir)
    if not found:
        return None
    _, slug, proj_dir, state_path, text = found
    m = re.search(r"^Mode:\s*([a-zA-Z0-9_-]+)", text, flags=re.MULTILINE)
    mode = m.group(1).strip().lower() if m else ""
    playbook = os.path.join(PLUGIN_ROOT, "skills", "deepwork", "references", f"mode-{mode}.md") if mode else ""
    clipped = text.strip()
    if len(clipped) > DEEPWORK_STATE_CAP:
        clipped = clipped[:DEEPWORK_STATE_CAP].rsplit("\n", 1)[0] + f"\n… (full state in {state_path})"
    lines = [
        f"Background: an active overclock Deepwork project '{slug}' exists in {proj_dir}.",
        "If the user's request continues this project, inspect the files there and follow its workflow; otherwise ignore it.",
    ]
    if playbook and os.path.isfile(playbook):
        lines.append(f"Active mode playbook ({mode}): {playbook}")
    lines.append("")
    lines.append(clipped)
    return "\n".join(lines)


def latest_checkpoint(event):
    if os.environ.get("OVERCLOCK_RESUME") == "off" or os.environ.get("OVERCLOCK_CHECKPOINT") == "off":
        return None
    # resume / compact already carry the conversation (or its summary): nothing to add.
    if event.get("source") not in ("startup", "clear"):
        return None
    path = event.get("transcript_path")
    if not path:
        return None
    pdir = project_dir(path)
    me = sid8(event.get("session_id"))
    try:
        files = [os.path.join(pdir, n) for n in os.listdir(pdir) if n.endswith(".md") and n != f"{me}.md"]
    except OSError:
        return None
    if not files:
        return None
    newest = max(files, key=os.path.getmtime)
    age = time.time() - os.path.getmtime(newest)
    if age > float(os.environ.get("OVERCLOCK_RESUME_DAYS", "7")) * 86400:
        return None
    text = open(newest).read()
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS].rsplit("\n", 1)[0] + f"\n… (rest in {newest})"
    try:
        with open(os.path.join(pdir, f".loaded-{me}"), "w") as f:
            f.write(newest)
    except OSError:
        pass
    return (f"Background: below is a checkpoint of an earlier Claude Code session in this project, saved {ago(age)}. "
            f"If the user's request continues that work, use it instead of asking them to repeat context; "
            f"otherwise ignore it.\n\n{text}")


def main():
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
    except ValueError:
        event = {}

    if is_antigravity(event):
        try:
            start_dir = event.get("cwd") or ((event.get("workspacePaths") or [None])[0])
            proj = active_project_context(start_dir)
            if not proj:
                print("{}")
            else:
                print(json.dumps({"injectSteps": [{"systemMessage": {"systemMessage": proj}}]}))
        except Exception:
            print("{}")
        return

    # Claude Code branch
    if event.get("source") in ("startup", "clear"):
        try:
            from idle_check import load_stats, save_stats
            st = load_stats()
            if st.get("last_hold") and time.time() - st["last_hold"] < 1800:
                st.update(ignored=0, last_hold=0)
                save_stats(st)
        except Exception:
            pass
    parts = []
    if os.environ.get("OVERCLOCK_RULES") != "off":
        parts.append(RULES)
    if os.environ.get("OVERCLOCK_TIERS") != "off":
        try:
            from tiers import block as tier_block
            tb = tier_block()
            if tb:
                parts.append(tb)
        except Exception:
            pass
    try:
        cp = latest_checkpoint(event)
    except Exception:
        cp = None
    if cp:
        parts.append(cp)

    source = event.get("source")
    if source in (None, "", "startup", "clear", "compact"):
        try:
            proj = active_project_context(event.get("cwd"))
        except Exception:
            proj = None
        if proj:
            parts.append(proj)

    if parts:
        combined = "\n\n".join(parts)
        if len(combined) > CLAUDE_TOTAL_CAP:
            combined = combined[:CLAUDE_TOTAL_CAP].rsplit("\n", 1)[0]
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                 "additionalContext": combined}}))


if __name__ == "__main__":
    main()
