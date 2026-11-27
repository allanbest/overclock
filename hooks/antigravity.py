#!/usr/bin/env python3
"""overclock for Antigravity (Gemini): one hook script, dispatched by hookEventName.

- SessionStart: lean working rules, the newest checkpoint for this workspace,
  and the active Deepwork project (if any).
- Stop: write a ~1-2 KB checkpoint of the conversation from its transcript
  (plain code, no model call), so a new conversation can carry on cheaply.
- PreToolUse: run noisy commands (tests, builds, installs) through ag_run.py,
  which trims long output and keeps the exit code. PostToolUse can't change
  output in Antigravity, so this is the only way to trim.

Model tiers are Claude-only; Antigravity has its own model routing.

Settings: OVERCLOCK_RULES=off, OVERCLOCK_CHECKPOINT=off, OVERCLOCK_RESUME=off,
OVERCLOCK_RESUME_DAYS=7, OVERCLOCK_OFF=1 (no trimming).
"""
import base64
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from checkpoint import clip  # noqa: E402

ROOT = os.path.expanduser(os.environ.get("OVERCLOCK_HOME") or os.environ.get("PLUGIN_DATA") or "~/.gemini/overclock")
KEEP_FILES = 12
MAX_INJECT = 2500

RULES = """overclock efficiency rules (quality first):
- Lead with the answer; no preamble or recap. Keep code, paths, numbers and errors exact.
- Batch independent tool calls. Search before opening files; read only the line ranges you need; don't re-read unchanged files.
- Run commands as-is (no head/tail): overclock trims long output from tests, builds and installs, keeping start, end and all error lines, plus a path to the full text. If a command was rewritten to run through overclock's ag_run.py, that's expected."""

EDIT_TOOLS = {"edit_file": "Path", "write_file": "Path", "replace_file_content": "TargetFile", "write_to_file": "TargetFile"}

# Commands whose output is often long and that finish on their own (never dev servers or watchers).
NOISY = re.compile(
    r"(^|[;&|(]\s*|\bthen\s+)("
    r"(npm|pnpm|yarn|bun)\s+(test|t|ci|install|i|add|run\s+(build|test|lint|typecheck|check))\b"
    r"|(python3?\s+-m\s+)?(pytest|unittest|tox|nox)\b|pip3?\s+install\b|uv\s+(pip\s+install|sync)\b"
    r"|cargo\s+(build|test|check|clippy)\b|go\s+(build|test|vet)\b|make\b|cmake\s+--build\b"
    r"|(\./)?gradlew?\s|mvn\s|docker\s+(build|compose\s+build)\b|tsc\b|jest\b|vitest\s+run\b"
    r"|eslint\b|ruff\b|mypy\b|brew\s+install\b|swift\s+(build|test)\b|xcodebuild\b|git\s+log\b)"
)
NEVER = re.compile(r"\b(watch|--watch|serve|dev\b|start\b)|OVERCLOCK_RAW|ag_run\.py")


def workspace(event):
    return event.get("cwd") or (event.get("workspacePaths") or [None])[0] or os.getcwd()


def project_dir(ws):
    slug = re.sub(r"[^A-Za-z0-9_.-]", "-", os.path.realpath(ws)).strip("-") or "default"
    return os.path.join(ROOT, "checkpoints", slug)


def sid8(cid):
    return re.sub(r"[^A-Za-z0-9]", "", cid or "")[:8] or "session"


# ---------- Stop: checkpoint ----------

def parse(transcript_path):
    s = {"prompts": [], "edited": [], "commands": [], "errors": [], "todos": None, "tools": 0, "last": ""}
    with open(transcript_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            kind = e.get("type")
            if kind == "USER_INPUT":
                m = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", e.get("content") or "", re.S)
                text = (m.group(1) if m else e.get("content") or "").strip()
                if text:
                    s["prompts"].append(text)
            elif kind == "ERROR_MESSAGE":
                msg = e.get("content") or e.get("error") or ""
                if msg.strip():
                    s["errors"].append(clip(msg, 120))
            elif kind == "PLANNER_RESPONSE":
                if e.get("content") and not e.get("tool_calls"):
                    s["last"] = e["content"]
                for t in e.get("tool_calls") or []:
                    s["tools"] += 1
                    name, args = t.get("name", ""), t.get("args") or {}
                    if name in EDIT_TOOLS and args.get(EDIT_TOOLS[name]):
                        p = str(args[EDIT_TOOLS[name]]).strip('"')
                        if p in s["edited"]:
                            s["edited"].remove(p)
                        s["edited"].append(p)
                    elif name == "run_command" and args.get("CommandLine"):
                        s["commands"].append(clip(str(args["CommandLine"]).strip('"'), 80))
                    elif name == "update_steps":
                        try:
                            steps = args.get("steps")
                            steps = json.loads(steps) if isinstance(steps, str) else steps
                            s["todos"] = [(x.get("status", ""), x.get("title", "")) for x in steps if isinstance(x, dict)]
                        except (ValueError, TypeError, AttributeError):
                            pass
    return s


def write_checkpoint(event):
    path = event.get("transcriptPath")
    if os.environ.get("OVERCLOCK_CHECKPOINT") == "off" or not path or not os.path.isfile(path):
        return
    s = parse(path)
    if len(s["prompts"]) < 2 and s["tools"] < 3:
        return  # quick questions never replace a real checkpoint
    ws = workspace(event)
    mark = {"completed": "x", "done": "x", "in_progress": ">", "pending": " "}
    out = ["# overclock checkpoint",
           f"Saved: {time.strftime('%Y-%m-%d %H:%M')} · conversation {sid8(event.get('conversationId'))} · folder {ws}"]
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
        base = os.path.realpath(ws) + os.sep
        rel = []
        for p in s["edited"][-8:]:
            rp = os.path.realpath(p)
            rel.append(rp[len(base):] if rp.startswith(base) else p.replace(os.path.expanduser("~"), "~"))
        out.append("Files edited (latest last): " + ", ".join(rel))
    if s["commands"]:
        out.append("Recent commands: " + " | ".join(f"`{c}`" for c in s["commands"][-3:]))
    if s["errors"]:
        out.append("Recent errors: " + " | ".join(s["errors"][-2:]))
    if s["last"]:
        out.append(f"End of last reply: {clip(s['last'][-500:], 500)}")
    out.append(f"Full transcript (large; search it for details, don't read it whole): {path}")
    pdir = project_dir(ws)
    os.makedirs(pdir, exist_ok=True)
    target = os.path.join(pdir, f"{sid8(event.get('conversationId'))}.md")
    with open(target + ".tmp", "w") as f:
        f.write("\n".join(out) + "\n")
    os.replace(target + ".tmp", target)
    files = sorted((os.path.join(pdir, n) for n in os.listdir(pdir) if n.endswith(".md")), key=os.path.getmtime)
    for old in files[:-KEEP_FILES]:
        os.remove(old)


# ---------- SessionStart ----------

def latest_checkpoint(event):
    if os.environ.get("OVERCLOCK_RESUME") == "off" or os.environ.get("OVERCLOCK_CHECKPOINT") == "off":
        return None
    pdir = project_dir(workspace(event))
    me = sid8(event.get("conversationId")) + ".md"
    try:
        files = [os.path.join(pdir, n) for n in os.listdir(pdir) if n.endswith(".md") and n != me]
    except OSError:
        return None
    if not files:
        return None
    newest = max(files, key=os.path.getmtime)
    age = time.time() - os.path.getmtime(newest)
    if age > float(os.environ.get("OVERCLOCK_RESUME_DAYS", "7")) * 86400:
        return None
    text = open(newest).read()[:MAX_INJECT]
    when = f"{age / 3600:.0f} hours ago" if age >= 3600 else f"{age / 60:.0f} minutes ago"
    return (f"Background: below is a checkpoint of an earlier conversation in this workspace, saved {when}. "
            f"If the user's request continues that work, use it instead of asking them to repeat context; "
            f"otherwise ignore it.\n\n{text}")


def session_start(event):
    parts = []
    if os.environ.get("OVERCLOCK_RULES") != "off":
        parts.append(RULES)
    for fn in (latest_checkpoint,):
        try:
            cp = fn(event)
            if cp:
                parts.append(cp)
        except Exception:
            pass
    try:
        from session_start import active_project_context
        proj = active_project_context(workspace(event))
        if proj:
            parts.append(proj)
    except Exception:
        pass
    if not parts:
        return {}
    return {"injectSteps": [{"systemMessage": {"systemMessage": "\n\n".join(parts)}}]}


# ---------- PreToolUse: trim noisy commands ----------

def pre_tool_use(event):
    if os.environ.get("OVERCLOCK_OFF"):
        return {}
    call = event.get("toolCall") or {}
    cmd = (call.get("args") or {}).get("CommandLine")
    if call.get("name") != "run_command" or not isinstance(cmd, str):
        return {}
    if not NOISY.search(cmd) or NEVER.search(cmd):
        return {}
    enc = base64.b64encode(cmd.encode("utf-8")).decode("ascii")
    runner = os.path.join(HERE, "ag_run.py")
    # Leave the permission decision to the user's own settings.
    return {"decision": "ask", "overwrite": {"CommandLine": f"python3 '{runner}' {enc}"}}


def main():
    raw = sys.stdin.read()
    try:
        event = json.loads(raw) if raw.strip() else {}
    except ValueError:
        event = {}
    name = event.get("hookEventName")
    out = {}
    try:
        if name == "SessionStart":
            out = session_start(event)
        elif name == "Stop":
            write_checkpoint(event)
        elif name == "PreToolUse":
            out = pre_tool_use(event)
    except Exception:
        out = {}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
