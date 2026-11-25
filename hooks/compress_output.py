#!/usr/bin/env python3
"""overclock PostToolUse hook: trim noisy Bash output before Claude reads it.

Every byte that enters the conversation is re-sent on every later turn, so a
2,000-line test log is paid for again and again. This hook:

1. Does lossless cleanup first: strips ANSI colour codes and progress-bar
   redraws, removes trailing spaces, minifies pretty-printed JSON.
2. If the output is still large, keeps the head, the tail, and every line that
   looks like an error/warning/failure (with a little context), collapses
   repeated lines, and saves the full original to a log file whose path is
   included, so nothing is lost.

It fails open: on any problem it prints nothing and the original output is used.
Skip trimming for one command by including OVERCLOCK_RAW in it
(e.g. `OVERCLOCK_RAW=1 npm test`), or for a session with env OVERCLOCK_OFF=1.
"""
import json
import os
import re
import sys
import tempfile

TRIM_ABOVE_CHARS = int(os.environ.get("OVERCLOCK_TRIM_ABOVE", "6000"))  # ~1.5k tokens
HEAD_LINES = 30
TAIL_LINES = 40
MAX_SIGNAL_LINES = 80
CONTEXT = 2

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")
SIGNAL = re.compile(
    r"(error|fail|failed|failure|exception|traceback|panic|fatal|warn(ing)?|"
    r"denied|not found|cannot|can't|unable|undefined|assert|expected|segfault|"
    r"exit code|exited with|✗|✘|×)",
    re.IGNORECASE,
)


def clean(text: str) -> str:
    text = ANSI.sub("", text)
    # Progress bars redraw with \r: keep only the final state of each line.
    text = "\n".join(line.rsplit("\r", 1)[-1] for line in text.split("\n"))
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    stripped = text.strip()
    if stripped[:1] in "{[" and len(stripped) > 2000:
        try:
            text = json.dumps(json.loads(stripped), separators=(",", ":"), ensure_ascii=False)
        except ValueError:
            pass
    return text


def collapse_repeats(lines):
    out, prev, count = [], None, 0
    for line in lines + [None]:
        if line == prev:
            count += 1
            continue
        if prev is not None:
            out.append(prev if count == 1 else f"{prev}  [×{count}]")
        prev, count = line, 1
    return out


def trim(text: str, log_path: str) -> str:
    lines = collapse_repeats(text.split("\n"))
    collapsed = "\n".join(lines)
    if len(collapsed) <= TRIM_ABOVE_CHARS:
        # Collapsing repeats was enough; nothing else needs cutting.
        return f"[overclock: repeated lines collapsed. Full output: {log_path}]\n{collapsed}"
    text = collapsed
    if len(lines) <= HEAD_LINES + TAIL_LINES + 10:
        # Few but very long lines: cut by characters instead.
        half = TRIM_ABOVE_CHARS // 2
        body = text[:half] + f"\n… [{len(text) - 2 * half:,} chars omitted] …\n" + text[-half:]
    else:
        keep = set(range(HEAD_LINES)) | set(range(len(lines) - TAIL_LINES, len(lines)))
        signal_hits = [i for i in range(HEAD_LINES, len(lines) - TAIL_LINES) if SIGNAL.search(lines[i])]
        for i in signal_hits[:MAX_SIGNAL_LINES]:
            keep.update(range(max(0, i - CONTEXT), min(len(lines), i + CONTEXT + 1)))
        body_lines, last = [], -1
        for i in sorted(keep):
            if i != last + 1:
                body_lines.append(f"… [{i - last - 1} lines omitted] …")
            body_lines.append(lines[i])
            last = i
        body = "\n".join(body_lines)
        if len(signal_hits) > MAX_SIGNAL_LINES:
            body += f"\n… [{len(signal_hits) - MAX_SIGNAL_LINES} more error/warning lines in the full log]"
    return (
        f"[overclock: output trimmed from {len(text):,} chars; head, tail and every error/warning line kept; "
        f"colour codes removed. Full output: {log_path}]\n{body}"
    )


def save_full(original: dict, tool_use_id: str) -> str:
    folder = os.path.join(tempfile.gettempdir(), "overclock-logs")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{re.sub(r'[^A-Za-z0-9_-]', '', tool_use_id) or 'output'}.log")
    with open(path, "w", encoding="utf-8") as f:
        f.write(original.get("stdout") or "")
        if original.get("stderr"):
            f.write("\n--- stderr ---\n" + original["stderr"])
    return path


def main() -> None:
    if os.environ.get("OVERCLOCK_OFF"):
        return
    event = json.load(sys.stdin)
    resp = event.get("tool_response")
    command = (event.get("tool_input") or {}).get("command", "")
    if not isinstance(resp, dict) or resp.get("isImage") or "OVERCLOCK_RAW" in command:
        return
    stdout, stderr = resp.get("stdout") or "", resp.get("stderr") or ""
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        return

    # Small outputs are left exactly as they are. Silently changing them (even
    # just removing colour codes) can make results look inconsistent with the
    # command that produced them, which costs more turns than it saves.
    if len(stdout) + len(stderr) <= TRIM_ABOVE_CHARS:
        return

    # Very large outputs: Claude Code has already saved the full text to a file
    # and passes us only the first part. Read the full file so error lines in
    # the middle aren't lost, and point Claude at that file instead of a copy.
    persisted = resp.get("persistedOutputPath")
    if isinstance(persisted, str) and os.path.isfile(persisted):
        with open(persisted, encoding="utf-8", errors="replace") as f:
            stdout = f.read()
        log_path = persisted
    else:
        log_path = save_full(resp, event.get("tool_use_id", ""))
    new_out, new_err = clean(stdout), clean(stderr)
    if len(new_out) > TRIM_ABOVE_CHARS // 2:
        new_out = trim(new_out, log_path)
    elif new_out != stdout:
        new_out = f"[overclock: colour codes/progress bars removed. Full output: {log_path}]\n{new_out}"
    if len(new_err) > TRIM_ABOVE_CHARS // 2:
        new_err = trim(new_err, log_path)

    if new_out == stdout and new_err == stderr and not persisted:
        return  # nothing to change: leave the original untouched

    updated = dict(resp)  # keep every field so the shape matches
    updated["stdout"], updated["stderr"] = new_out, new_err
    # Our compact version replaces Claude Code's "output too large" preview.
    updated.pop("persistedOutputPath", None)
    updated.pop("persistedOutputSize", None)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": updated}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # fail open: the original output is used
