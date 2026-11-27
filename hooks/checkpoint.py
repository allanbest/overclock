#!/usr/bin/env python3
"""overclock checkpoint: keep a tiny "where we are" note for every real session.

Runs on Stop (end of each Claude turn), while the conversation is still cached.
It uses plain code, no model call: it reads the session transcript and writes
~1-2 KB to ~/.claude/overclock/checkpoints/<project>/<session>.md with the goal,
recent requests, plan/todos, edited files, recent commands and errors, and the
end of the last reply.

When you open a new chat (or type /clear) in the same project, session_start.py
loads the newest checkpoint, so you can carry on without re-reading the whole
old conversation. That's the cheap way back after the cache has expired.

It prints nothing and never blocks; any error is ignored.

Settings: OVERCLOCK_CHECKPOINT=off disables it.
"""
import json
import os
import re
import sys
from datetime import datetime

ROOT = os.path.expanduser(os.environ.get("OVERCLOCK_HOME", "~/.claude/overclock"))
HEAD_BYTES = 400_000
TAIL_BYTES = 4_000_000
KEEP_FILES = 12

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SKIP_PREFIXES = ("<command-", "<local-command", "<system-reminder>", "Caveat:", "[Request interrupted",
                 "<task-notification>", "<agent-message", "<side-sessions-event>", "<ci-monitor-event>")


def project_dir(transcript_path):
    slug = os.path.basename(os.path.dirname(transcript_path)) or "default"
    return os.path.join(ROOT, "checkpoints", re.sub(r"[^A-Za-z0-9_.-]", "-", slug))


def sid8(session_id):
    return re.sub(r"[^A-Za-z0-9]", "", session_id or "")[:8] or "session"


def read_lines(path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        if size <= HEAD_BYTES + TAIL_BYTES:
            data = f.read()
        else:
            head = f.read(HEAD_BYTES)
            f.seek(size - TAIL_BYTES)
            data = head.rsplit(b"\n", 1)[0] + b"\n" + f.read().split(b"\n", 1)[-1]
    for line in data.decode("utf-8", "replace").split("\n"):
        if line.strip():
            try:
                yield json.loads(line)
            except ValueError:
                continue


def clip(text, n):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def user_text(content):
    """Return the human-typed text of a user entry, or None for tool results and wrappers."""
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        content = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    if not isinstance(content, str):
        return None
    content = re.sub(r"<system-reminder>.*?</system-reminder>", "", content, flags=re.S).strip()
    if not content or content.startswith(SKIP_PREFIXES):
        return None
    return content


def parse(transcript_path):
    s = {"prompts": [], "edited": [], "commands": [], "errors": [], "todos": None, "tools": 0}
    tool_names = {}
    for e in read_lines(transcript_path):
        if e.get("isSidechain") or e.get("isMeta") or e.get("isCompactSummary"):
            continue
        msg = e.get("message") or {}
        content = msg.get("content")
        if e.get("type") == "user":
            text = user_text(content)
            if text:
                s["prompts"].append(text)
            elif isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error"):
                        c = b.get("content")
                        if isinstance(c, list):
                            c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
                        s["errors"].append(f"{tool_names.get(b.get('tool_use_id'), 'tool')}: {clip(str(c), 120)}")
        elif e.get("type") == "assistant" and isinstance(content, list):
            for b in content:
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                s["tools"] += 1
                name, inp = b.get("name", ""), b.get("input") or {}
                tool_names[b.get("id")] = name
                if name in EDIT_TOOLS and inp.get("file_path"):
                    p = inp["file_path"]
                    if p in s["edited"]:
                        s["edited"].remove(p)
                    s["edited"].append(p)
                elif name == "Bash" and inp.get("command"):
                    s["commands"].append(clip(inp["command"], 80))
                elif name == "TodoWrite" and isinstance(inp.get("todos"), list):
                    s["todos"] = [(t.get("status", ""), t.get("content", "")) for t in inp["todos"] if isinstance(t, dict)]
                elif name.endswith("update_plan") and isinstance(inp.get("items"), list):
                    s["todos"] = [(t.get("status", ""), t.get("content", "")) for t in inp["items"] if isinstance(t, dict)]
    return s


def carried_goal(pdir, session_id):
    """If this session started from another session's checkpoint, keep that session's goal."""
    try:
        src = open(os.path.join(pdir, f".loaded-{sid8(session_id)}")).read().strip()
        for line in open(src):
            if line.startswith(("Goal", "Earlier goal")):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return None


def build(event, s, pdir):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    mark = {"completed": "x", "in_progress": ">", "pending": " "}
    out = [f"# overclock checkpoint",
           f"Saved: {now} · session {sid8(event.get('session_id'))} · folder {event.get('cwd', '')}"]
    earlier = carried_goal(pdir, event.get("session_id"))
    if earlier:
        out.append(f"Earlier goal: {clip(earlier, 300)}")
    if s["prompts"]:
        out.append(f"Goal (first request): {clip(s['prompts'][0], 300)}")
        recent = s["prompts"][1:][-3:]
        if recent:
            out.append("Latest requests:")
            out += [f"- {clip(p, 200)}" for p in recent]
    if s["todos"]:
        out.append("Plan:")
        out += [f"- [{mark.get(st, ' ')}] {clip(c, 90)}" for st, c in s["todos"][:10]]
    if s["edited"]:
        cwd = os.path.realpath(event.get("cwd") or "/") + os.sep
        rel = []
        for p in s["edited"][-8:]:
            rp = os.path.realpath(p)
            rel.append(rp[len(cwd):] if rp.startswith(cwd) else p.replace(os.path.expanduser("~"), "~"))
        out.append("Files edited (latest last): " + ", ".join(rel))
    if s["commands"]:
        out.append("Recent commands: " + " | ".join(f"`{c}`" for c in s["commands"][-3:]))
    if s["errors"]:
        out.append("Recent errors: " + " | ".join(s["errors"][-2:]))
    last = event.get("last_assistant_message")
    if last:
        out.append(f"End of last reply: {clip(last[-500:], 500)}")
    out.append(f"Full transcript (large; grep it for details, don't read it whole): {event.get('transcript_path')}")
    return "\n".join(out) + "\n"


def main():
    if os.environ.get("OVERCLOCK_CHECKPOINT") == "off" or os.environ.get("OVERCLOCK_OFF"):
        return
    event = json.load(sys.stdin)
    path = event.get("transcript_path")
    if not path or not os.path.isfile(path):
        return
    s = parse(path)
    # Only sessions with real work are worth resuming; a quick question never overwrites anything.
    if len(s["prompts"]) < 2 and s["tools"] < 3:
        return
    pdir = project_dir(path)
    os.makedirs(pdir, exist_ok=True)
    target = os.path.join(pdir, f"{sid8(event.get('session_id'))}.md")
    tmp = target + ".tmp"
    with open(tmp, "w") as f:
        f.write(build(event, s, pdir))
    os.replace(tmp, target)
    # Keep the folder small.
    for ext, keep in ((".md", KEEP_FILES), (".loaded-", 30)):
        files = sorted((os.path.join(pdir, n) for n in os.listdir(pdir) if ext in n and not n.endswith(".tmp")),
                       key=os.path.getmtime)
        for old in files[:-keep]:
            os.remove(old)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open
