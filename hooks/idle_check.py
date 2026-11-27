#!/usr/bin/env python3
"""overclock UserPromptSubmit hook: warn before an expensive "cold" resume.

Claude keeps a recent conversation in a prompt cache, which makes re-reading it
cheap. On a Claude plan the main conversation's cache lasts about an hour. After
a longer break, the next message makes Claude re-process the whole conversation
at full cost. In a big session that's a large chunk of your usage limit, spent
before Claude even starts on your new message.

When the session has been idle longer than the cache lifetime AND the
conversation is large, this hook holds the message once and explains the
options. Sending the same message again goes through normally.

Claude Code's own "idle compaction" (on by default for conversations over
~200k tokens in interactive sessions) summarizes a big idle conversation just
before the cache expires. If that already happened, this hook stays quiet.

Settings (environment variables, optional):
  OVERCLOCK_IDLE_MINUTES     idle time before warning (default 60)
  OVERCLOCK_IDLE_MIN_TOKENS  only warn above this context size (default 60000)
  OVERCLOCK_IDLE_MODE        "auto" (default): hold the message once, but after you've sent it
                             anyway twice in a row, only show a note (until you next take the advice);
                             "hold": always hold once; "note": never hold
  OVERCLOCK_OFF=1            disable
"""
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone

IDLE_MINUTES = float(os.environ.get("OVERCLOCK_IDLE_MINUTES", "60"))
MIN_TOKENS = int(os.environ.get("OVERCLOCK_IDLE_MIN_TOKENS", "60000"))
MODE = os.environ.get("OVERCLOCK_IDLE_MODE", "auto")
IGNORE_LIMIT = 2  # in auto mode: after this many "sent it anyway" in a row, only show a note
STATS = os.path.join(os.path.expanduser(os.environ.get("OVERCLOCK_HOME", "~/.claude/overclock")), "idle-stats.json")


def load_stats():
    try:
        with open(STATS) as f:
            return json.load(f)
    except Exception:
        return {"ignored": 0, "last_hold": 0}


def save_stats(st):
    try:
        os.makedirs(os.path.dirname(STATS), exist_ok=True)
        with open(STATS, "w") as f:
            json.dump(st, f)
    except OSError:
        pass
TAIL_BYTES = 400_000


def last_reply(transcript_path):
    """Return (timestamp, context_tokens) of the latest assistant reply, or (None, 0)."""
    with open(transcript_path, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - TAIL_BYTES))
        lines = f.read().decode("utf-8", "replace").split("\n")
    for line in reversed(lines):
        if '"compact_boundary"' in line:
            # The conversation was compacted after the last reply (for example by
            # Claude Code's built-in idle compaction), so the old size no longer applies.
            return None, 0
        if '"assistant"' not in line or '"usage"' not in line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        u = (e.get("message") or {}).get("usage") or {}
        if e.get("type") != "assistant" or not u or not e.get("timestamp"):
            continue
        tokens = u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
        ts = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
        return ts, tokens
    return None, 0


def state_file(session_id):
    folder = os.path.join(tempfile.gettempdir(), "overclock-state")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, re.sub(r"[^A-Za-z0-9_-]", "", session_id or "session") + ".idle")


def main():
    if os.environ.get("OVERCLOCK_OFF"):
        return
    event = json.load(sys.stdin)
    prompt = (event.get("prompt") or "").strip()
    path = event.get("transcript_path")
    if not path or not os.path.isfile(path) or prompt.startswith("/"):
        return  # slash commands (/clear, /compact, /overclock:handoff…) go straight through

    ts, tokens = last_reply(path)
    if ts is None or tokens < MIN_TOKENS:
        return
    idle_min = (datetime.now(timezone.utc) - ts).total_seconds() / 60
    if idle_min < IDLE_MINUTES:
        return

    # Hold only once per idle gap: if we already warned for this same gap, let it through.
    marker = state_file(event.get("session_id", ""))
    gap_id = ts.isoformat()
    try:
        if open(marker).read().strip() == gap_id:
            st = load_stats()  # the user re-sent after a hold: they chose to continue here
            st["ignored"] = st.get("ignored", 0) + 1
            save_stats(st)
            return
    except OSError:
        pass

    hours = idle_min / 60
    idle_txt = f"{hours:.1f} hours" if hours >= 1.5 else f"{idle_min:.0f} minutes"
    size_txt = f"{tokens / 1000:.0f}k-token"
    cp_note = ""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from checkpoint import project_dir, sid8
        cp = os.path.join(project_dir(path), f"{sid8(event.get('session_id'))}.md")
        if os.path.isfile(cp):
            cp_note = f"~{os.path.getsize(cp) // 4 + 300} tokens"
    except Exception:
        pass
    if cp_note:
        cheap = f"/clear or a new chat picks up from overclock's checkpoint ({cp_note} instead of {size_txt.split('-')[0]})"
    else:
        cheap = "a new chat is cheapest if you don't need this conversation's details"
    advice = (f"overclock: idle {idle_txt}, cache expired. Continuing here re-reads the whole {size_txt} chat "
              f"at full cost; {cheap}.")
    with open(marker, "w") as f:
        f.write(gap_id)

    st = load_stats()
    mode = MODE
    if mode == "auto":
        mode = "note" if st.get("ignored", 0) >= IGNORE_LIMIT else "hold"
    st["last_hold"] = datetime.now(timezone.utc).timestamp()  # time of the last warning (hold or note)
    save_stats(st)
    if mode == "note":
        print(json.dumps({"systemMessage": advice}))
        return
    preview = prompt if len(prompt) <= 300 else prompt[:300] + "…"
    print(json.dumps({"decision": "block", "reason": advice + " Send your message again to continue here "
                      f"(you won't be asked twice).\n\nYour message (not sent yet):\n{preview}"}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: never get in the way because of a bug here
