#!/usr/bin/env python3
"""Measure overclock's effect on Claude subscription usage limits (not API dollars).

Claude Code reports your live usage-limit levels in every session
(`rate_limit_event` in stream-json output: five_hour and seven_day utilization).
This script runs the same batch of tasks with and without overclock, in
alternating blocks (A B A B …), and reads the meter before and after each block.

It uses YOUR plan's limits. Don't use Claude anywhere else while it runs, or your
usage gets mixed into the numbers.

Usage:
    python3 bench/quota_ab.py --claude /path/to/claude --blocks 4 --model sonnet
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.dirname(HERE)

REPORT_PY = r'''import sys, random
random.seed(7)
n = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
warn_at = {n // 5: ("SKU-4471", "stock below reorder point (3 < 10)"),
           n // 2: ("SKU-0932", "price changed 41% in one day"),
           (4 * n) // 5: ("SKU-7718", "duplicate barcode 0049000028911")}
print("inventory report v2  --  scanning records")
for i in range(n):
    if i in warn_at:
        sku, why = warn_at[i]
        print(f"\x1b[33mWARN\x1b[0m  record {i:05d} {sku}: {why}")
    else:
        print(f"\x1b[32mINFO\x1b[0m  record {i:05d} SKU-{random.randint(1000,9999)} ok  qty={random.randint(10,500):>4} price={random.uniform(1,99):6.2f}")
print(f"done: {n} records, {len(warn_at)} warnings")
'''

TASKS = {
    "big-log": ("Run python3 report.py and tell me which records triggered warnings and why.",
                lambda r: all(s in r for s in ("4471", "0932", "7718"))),
    "mid-log": ("Run python3 report.py 260 and tell me which records triggered warnings and why.",
                lambda r: all(s in r for s in ("4471", "0932", "7718"))),
    "chat": ("Explain the difference between TCP and UDP to a beginner, and when you'd use each.",
             lambda r: "UDP" in r),
}
SETTINGS = json.dumps({"enabledPlugins": {"verisource@verisource": False}})


def run_claude(claude, args, cwd):
    p = subprocess.run([claude, *args], cwd=cwd, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, timeout=600)
    events = []
    for line in p.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    return events


def read_meter(claude, workdir):
    """Tiny Haiku call; returns (five_hour, seven_day, five_hour_resets_at)."""
    ev = run_claude(claude, ["-p", "Reply with just: ok", "--model", "haiku", "--settings", SETTINGS,
                             "--output-format", "stream-json", "--verbose"], workdir)
    for e in ev:
        if e.get("type") == "rate_limit_event":
            w = e["rate_limit_info"].get("unifiedWindows", {})
            return (w["five_hour"]["utilization"], w["seven_day"]["utilization"], w["five_hour"]["resetsAt"])
    raise RuntimeError("no rate_limit_event in output (are you signed in with a Claude plan?)")


def one_run(claude, model, arm, task, root):
    prompt, check = TASKS[task]
    d = tempfile.mkdtemp(prefix=f"{task}-{arm}-", dir=root)
    with open(os.path.join(d, "report.py"), "w") as f:
        f.write(REPORT_PY)
    args = ["-p", prompt, "--model", model, "--settings", SETTINGS,
            "--allowedTools", "Bash,Read,Grep,Glob,Agent", "--output-format", "stream-json", "--verbose"]
    if arm == "overclock":
        args += ["--plugin-dir", PLUGIN_DIR]
    ev = run_claude(claude, args, d)
    res = next((e for e in ev if e.get("type") == "result"), {})
    u = res.get("usage", {})
    return {
        "task": task, "arm": arm, "ok": bool(check(res.get("result", ""))),
        "turns": res.get("num_turns"), "cost": res.get("total_cost_usd", 0.0),
        "cache_write": u.get("cache_creation_input_tokens", 0), "cache_read": u.get("cache_read_input_tokens", 0),
        "output": u.get("output_tokens", 0),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claude", default=shutil.which("claude") or "claude")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--blocks", type=int, default=4, help="alternating blocks; even number")
    ap.add_argument("--reps", type=int, default=2, help="runs of each task per block")
    ap.add_argument("--out", default="quota_results.json")
    a = ap.parse_args()

    root = tempfile.mkdtemp(prefix="overclock-quota-")
    blocks = []
    before = read_meter(a.claude, root)
    for b in range(a.blocks):
        arm = "baseline" if b % 2 == 0 else "overclock"
        jobs = [t for t in TASKS for _ in range(a.reps)]
        print(f"block {b + 1}/{a.blocks} [{arm}]: {len(jobs)} runs …", flush=True)
        with ThreadPoolExecutor(max_workers=3) as ex:
            runs = list(ex.map(lambda t: one_run(a.claude, a.model, arm, t, root), jobs))
        time.sleep(5)
        after = read_meter(a.claude, root)
        reset = after[2] != before[2]
        blocks.append({"arm": arm, "five_hour_delta": round(after[0] - before[0], 4),
                       "seven_day_delta": round(after[1] - before[1], 4), "window_reset": reset, "runs": runs})
        print(f"  5h {before[0]:.2f}->{after[0]:.2f}  7d {before[1]:.2f}->{after[1]:.2f}"
              f"{'  (5h window reset: block excluded)' if reset else ''}", flush=True)
        before = after

    summary = {}
    for arm in ("baseline", "overclock"):
        bs = [x for x in blocks if x["arm"] == arm and not x["window_reset"]]
        runs = [r for x in bs for r in x["runs"]]
        summary[arm] = {
            "blocks": len(bs),
            "five_hour_pct_used": round(100 * sum(x["five_hour_delta"] for x in bs), 2),
            "seven_day_pct_used": round(100 * sum(x["seven_day_delta"] for x in bs), 2),
            "api_equiv_cost": round(sum(r["cost"] for r in runs), 4),
            "correct": f"{sum(r['ok'] for r in runs)}/{len(runs)}",
        }
    json.dump({"model": a.model, "summary": summary, "blocks": blocks}, open(a.out, "w"), indent=2)
    print(json.dumps(summary, indent=2))
    shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
