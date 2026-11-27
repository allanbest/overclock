#!/usr/bin/env python3
"""Run a command for Antigravity and trim its output if it's long.

Antigravity's PostToolUse hook can't change a tool's output, so overclock's
PreToolUse hook rewrites noisy commands (tests, builds, installs) to run
through this wrapper instead. Short output passes through unchanged; long
output is trimmed the same way as in Claude Code (start, end, every
error/warning line, repeats collapsed) and the full text is saved to a file.
The original exit code is kept.

Usage: ag_run.py <base64-encoded command>
"""
import base64
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compress_output import TRIM_ABOVE_CHARS, trim  # noqa: E402


def main():
    cmd = base64.b64decode(sys.argv[1]).decode("utf-8")
    p = subprocess.run(["/bin/sh", "-c", cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode("utf-8", "replace")
    if len(out) > TRIM_ABOVE_CHARS:
        folder = os.path.join(tempfile.gettempdir(), "overclock-logs")
        os.makedirs(folder, exist_ok=True)
        fd, log = tempfile.mkstemp(prefix="ag-", suffix=".log", dir=folder)
        with os.fdopen(fd, "w") as f:
            f.write(out)
        try:
            out = trim(out, log)
        except Exception:
            pass  # fall back to the untrimmed output
    sys.stdout.write(out)
    sys.stdout.flush()
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
