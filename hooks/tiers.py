#!/usr/bin/env python3
"""overclock tiers: one setting that decides which Claude model does which kind of work.

The main chat stays on one model (switching models mid-chat throws away the
prompt cache and re-reads everything at full price). Routing happens through
helpers: every overclock:scout / overclock:worker call gets an explicit model
picked from the active tier's table.

Usage:
  tiers.py show            print the current tier and the options
  tiers.py set <tier>      save a tier (low, medium, high, extra, max), or `off`
  tiers.py block           print the routing block injected at session start
  tiers.py fable on|off    allow the Fable tiers (extra, max); off by default

Settings:
  OVERCLOCK_TIER=<tier>    override the saved tier for this shell/session
  OVERCLOCK_FABLE=1 / 0    force Fable detection on or off
  OVERCLOCK_TIERS=off      don't inject the routing block
"""
import json
import os
import sys

ROOT = os.path.expanduser(os.environ.get("OVERCLOCK_HOME", "~/.claude/overclock"))
TIER_FILE = os.path.join(ROOT, "tier")
DEFAULT = "low"

TIERS = {
    "low": {
        "advisor": "off",
        "advisor_rule": "Only call the advisor tool (if present) when genuinely stuck.",
        "label": "Save usage",
        "main": "sonnet",
        "fable": False,
        "routes": [
            ("lookups, file search, listing, simple mechanical edits", "haiku"),
            ("normal analysis, research, coding", "sonnet"),
            ("only the single hardest piece, when Sonnet would likely fail", "opus"),
        ],
        "note": "Split work rarely; doing it yourself is usually cheapest.",
    },
    "medium": {
        "advisor": "off",
        "advisor_rule": "Call the advisor tool (if present) at most once per task, before the hardest decision.",
        "label": "Balanced",
        "main": "sonnet",
        "fable": False,
        "routes": [
            ("pure file search only", "haiku"),
            ("default for analysis, research, coding", "sonnet"),
            ("hard reasoning, tricky debugging, design decisions, final review", "opus"),
        ],
        "note": "",
    },
    "high": {
        "advisor": "off",
        "advisor_rule": "Call the advisor tool (if present) at most once per task, before the hardest decision.",
        "label": "Quality first",
        "main": "opus",
        "fable": False,
        "routes": [
            ("routine offload: searches, boilerplate, running tests, summarizing", "sonnet"),
            ("all substantive work", "opus"),
        ],
        "note": "Don't use Haiku.",
    },
    "extra": {
        "advisor": "fable",
        "advisor_rule": "Use the advisor tool (if present) before hard decisions and once before finishing.",
        "label": "Quality + Fable for the hardest parts",
        "main": "opus",
        "fable": True,
        "routes": [
            ("routine offload: searches, boilerplate, running tests", "sonnet"),
            ("default substantive work", "opus"),
            ("the hardest pieces: architecture, stubborn bugs, proofs, final review", "fable"),
        ],
        "note": "Don't use Haiku.",
    },
    "max": {
        "advisor": "off",
        "advisor_rule": "",
        "label": "Best quality (Fable)",
        "main": "fable",
        "fable": True,
        "routes": [
            ("mechanical bulk work only", "sonnet"),
            ("substantive helper work", "opus"),
            ("anything hard or high-stakes", "fable"),
        ],
        "note": "Don't use Haiku.",
    },
}
ORDER = ["low", "medium", "high", "extra", "max"]
MAIN_NAMES = {"haiku": "Haiku", "sonnet": "Sonnet", "opus": "Opus", "fable": "Fable"}


FABLE_FILE = os.path.join(ROOT, "fable")


def fable_listed():
    """Free check: does Claude Code's cached model list for this account include Fable?"""
    try:
        with open(os.path.expanduser("~/.claude.json")) as f:
            d = json.load(f)
        return any("fable" in json.dumps(o).lower() for o in (d.get("additionalModelOptionsCache") or []))
    except Exception:
        return False


def has_fable():
    """Fable is opt-in: being listed isn't enough, because on many plans it bills usage credits.
    On only after `tiers.py fable on` (or OVERCLOCK_FABLE=1)."""
    forced = os.environ.get("OVERCLOCK_FABLE")
    if forced in ("0", "1"):
        return forced == "1"
    try:
        return open(FABLE_FILE).read().strip() == "on"
    except OSError:
        return False


def current_advisor():
    """The advisorModel from the user's Claude Code settings ('' when off)."""
    try:
        with open(os.path.expanduser("~/.claude/settings.json")) as f:
            return (json.load(f).get("advisorModel") or "").strip()
    except Exception:
        return ""


def advisor_advice(t):
    want, have = TIERS[t]["advisor"], current_advisor() or "off"
    if want == have:
        return ""
    if want == "off":
        return (f"Advisor: your settings send the whole conversation to {have} as an advisor several times per task, "
                f"which can cost more than the work itself. Tier '{t}' recommends turning it off (run /advisor).")
    return f"Advisor: tier '{t}' recommends {want} as the advisor model (currently {have}; run /advisor)."


def saved_tier():
    t = (os.environ.get("OVERCLOCK_TIER") or "").strip().lower()
    if t in TIERS:
        return t
    try:
        t = open(TIER_FILE).read().strip().lower()
        if t in TIERS:
            return t
    except OSError:
        pass
    return DEFAULT


def effective_tier():
    """Return (tier, note). Fable tiers fall back to high when Fable isn't available."""
    t = saved_tier()
    if TIERS[t]["fable"] and not has_fable():
        return "high", f"'{t}' needs Fable, which is turned off; using 'high'."
    return t, ""


def tiers_off():
    try:
        return open(TIER_FILE).read().strip().lower() == "off" and not os.environ.get("OVERCLOCK_TIER")
    except OSError:
        return False


def block():
    if tiers_off():
        return ""
    t, fallback = effective_tier()
    cfg = TIERS[t]
    lines = [f"overclock model tier: {t} ({cfg['label']}). Recommended main-chat model: {MAIN_NAMES[cfg['main']]}.",
             "When delegating to overclock:scout or overclock:worker, always pass `model` explicitly:"]
    lines += [f"- {what} → {model}" for what, model in cfg["routes"]]
    lines.append("Hard = deep multi-step reasoning, already failed once, or high-stakes. "
                 "Never switch the main chat's model to route work; use helpers.")
    if cfg["note"]:
        lines.append(cfg["note"])
    if cfg["advisor_rule"]:
        lines.append(cfg["advisor_rule"])
    if fallback:
        lines.append(fallback)
    return "\n".join(lines)


def show():
    t, fallback = effective_tier()
    fable = has_fable()
    if tiers_off():
        return "Tiers are off. Turn on with `set low|medium|high` (or extra/max with Fable on)."
    out = [f"Current tier: {saved_tier()}" + (f" (running as {t}: Fable not available)" if fallback else ""),
           f"Fable tiers: {'on' if fable else 'off'}"
           + ("" if fable else (" (Fable is listed for your account but may need usage credits; "
                                "turn on with `fable on`)" if fable_listed() else "")),
           f"Advisor model in your settings: {current_advisor() or 'off'}", "", "Tiers:"]
    for name in ORDER:
        cfg = TIERS[name]
        if cfg["fable"] and not fable:
            continue
        models = " / ".join(sorted({m for _, m in cfg["routes"]}, key=["haiku", "sonnet", "opus", "fable"].index))
        out.append(f"  {name:<6} {cfg['label']:<38} main {MAIN_NAMES[cfg['main']]:<6} helpers {models:<22} advisor {cfg['advisor']}")
    tip = advisor_advice(t)
    if tip:
        out += ["", tip]
    return "\n".join(out)


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "show"
    if cmd == "fable":
        v = (argv[2] if len(argv) > 2 else "").strip().lower()
        if v not in ("on", "off"):
            print("Use: fable on | fable off")
            return 1
        os.makedirs(ROOT, exist_ok=True)
        with open(FABLE_FILE, "w") as f:
            f.write(v + "\n")
        print(f"Fable tiers turned {v}." + (" Fable may bill usage credits on your plan." if v == "on" else ""))
        return 0
    if cmd == "set":
        t = (argv[2] if len(argv) > 2 else "").strip().lower()
        if t == "off":
            os.makedirs(ROOT, exist_ok=True)
            with open(TIER_FILE, "w") as f:
                f.write("off\n")
            print("Tiers turned off: new chats won't get routing rules; helpers use their defaults "
                  "(scout Haiku, worker Sonnet). Turn back on with `set <tier>`.")
            return 0
        if t not in TIERS:
            print(f"Unknown tier '{t}'. Choose one of: {', '.join(ORDER)}")
            return 1
        if TIERS[t]["fable"] and not has_fable():
            print(f"'{t}' needs Fable, which is turned off (it may bill usage credits). "
                  f"Turn it on with `tiers.py fable on` if you have credits. Tier not changed.")
            return 1
        os.makedirs(ROOT, exist_ok=True)
        with open(TIER_FILE, "w") as f:
            f.write(t + "\n")
        print(f"Saved tier: {t}. New sessions load it automatically.\n")
        print(block())
        tip = advisor_advice(t)
        if tip:
            print("\n" + tip)
        return 0
    if cmd == "block":
        print(block())
        return 0
    print(show())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
