#!/usr/bin/env python3
"""Deterministic project state CLI for overclock Deepwork workflows.

Zero external dependencies (Python 3 stdlib only). Manages `.overclock/projects/<slug>/`
and `.overclock/active` so long-horizon projects stay structured and cheap to resume
across fresh sessions in both Claude Code and Antigravity.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime

MODES = ("science", "build", "research")
MAX_STATE_LINES = 30
MAX_STATE_CHARS = 1800
REQUIRED_STATE_FIELDS = ("Status:", "Mode:", "Goal:", "Next Step:")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def sanitize_slug(raw: str) -> str:
    if not raw or "/" in raw or "\\" in raw or ".." in raw:
        raise ValueError(f"Invalid slug {raw!r}: must be a single path segment without slashes or '..'")
    slug = re.sub(r"[^a-z0-9-]+", "-", raw.strip().lower()).strip("-")
    if not slug or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise ValueError(f"Invalid slug {raw!r}: must contain lowercase letters or digits")
    return slug


def find_workspace_root(cwd: str) -> str:
    """Walk upward from cwd looking for .overclock/active, .overclock/, or .git."""
    start = os.path.abspath(cwd or os.getcwd())
    cur = start
    overclock_dir = None
    git_dir = None
    while True:
        if os.path.isfile(os.path.join(cur, ".overclock", "active")):
            return cur
        if overclock_dir is None and os.path.isdir(os.path.join(cur, ".overclock")):
            overclock_dir = cur
        if git_dir is None and os.path.exists(os.path.join(cur, ".git")):
            git_dir = cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return overclock_dir or git_dir or start


def project_paths(root: str, slug: str) -> dict:
    base = os.path.join(root, ".overclock", "projects", slug)
    return {
        "root": root,
        "overclock": os.path.join(root, ".overclock"),
        "active_file": os.path.join(root, ".overclock", "active"),
        "base": base,
        "work": os.path.join(base, "work"),
        "brief": os.path.join(base, "brief.md"),
        "state": os.path.join(base, "state.md"),
        "decisions": os.path.join(base, "decisions.md"),
        "lab": os.path.join(base, "lab.md"),
        "experiments": os.path.join(base, "experiments"),
        "spec": os.path.join(base, "spec.md"),
        "tasks": os.path.join(base, "tasks.md"),
        "plan": os.path.join(base, "plan.md"),
        "notes": os.path.join(base, "notes"),
    }


def render_brief(slug: str, mode: str, goal: str) -> str:
    return (
        f"# Project Brief: {slug}\n\n"
        f"- **Mode:** {mode}\n"
        f"- **Created:** {now_str()}\n"
        f"- **Goal:** {goal}\n\n"
        f"## Scope & Constraints\n"
        f"- (Add hard constraints, datasets, target runtime, or budget limits)\n\n"
        f"## Success Criteria\n"
        f"- (Define concrete, verifiable completion criteria)\n\n"
        f"## Prior Art / References\n"
        f"- (Links, papers, DOIs, or existing modules)\n"
    )


def render_state(slug: str, mode: str, goal: str, status: str = "active") -> str:
    key_files = {
        "science": "brief.md, lab.md, decisions.md",
        "build": "brief.md, spec.md, tasks.md, decisions.md",
        "research": "brief.md, plan.md, decisions.md, notes/",
    }[mode]
    next_step = {
        "science": "Confirm framing/baseline in lab.md and define falsifiable H1 before running.",
        "build": "Lock spec.md contracts and implement walking skeleton (T1) in tasks.md.",
        "research": "Decompose sub-questions in plan.md and gather verified sources into notes/.",
    }[mode]
    return (
        f"# Project State: {slug}\n"
        f"Status: {status}\n"
        f"Mode: {mode}\n"
        f"Phase: framing\n"
        f"Updated: {now_str()}\n"
        f"Goal: {goal}\n"
        f"Active: Initial framing and baseline setup\n"
        f"Completed: (none yet)\n"
        f"Dead Ends / Avoid: (none yet)\n"
        f"Next Step: {next_step}\n"
        f"Key Files: {key_files}\n"
    )


def render_decisions(slug: str, mode: str) -> str:
    return (
        f"# Decisions & Lessons: {slug}\n\n"
        f"| Date | Type | Decision / Root Cause | Rationale / Evidence |\n"
        f"|---|---|---|---|\n"
        f"| {now_str()} | init | Started project in `{mode}` mode | Initialized via deepwork CLI |\n"
    )


def scaffold_mode_files(paths: dict, slug: str, mode: str, goal: str) -> list:
    created = []
    if mode == "science":
        os.makedirs(paths["experiments"], exist_ok=True)
        if not os.path.exists(paths["lab"]):
            with open(paths["lab"], "w", encoding="utf-8") as f:
                f.write(
                    f"# Lab Notebook: {slug}\n\n"
                    f"## Proposal & Baseline\n"
                    f"- **Goal:** {goal}\n"
                    f"- **Baseline:** (record minimal working baseline command + metric before testing hypotheses)\n\n"
                    f"## Hypothesis Registry\n"
                    f"| ID | Hypothesis | Prediction & Falsification Criterion | Status | Evidence |\n"
                    f"|---|---|---|---|---|\n"
                    f"| H1 | | | proposed | |\n\n"
                    f"## Experiment / Derivation Log\n"
                    f"### E1 — Baseline\n"
                    f"- **Hypothesis:** Baseline measurement\n"
                    f"- **Command / Artifact:** `...` (`experiments/E1/`)\n"
                    f"- **Result:** \n"
                    f"- **Reflection:** \n\n"
                    f"## Dead Ends & Refuted Approaches\n"
                    f"- (Record every failed or refuted idea + why, so it is never retried blindly)\n"
                )
            created.append("lab.md")
    elif mode == "build":
        if not os.path.exists(paths["spec"]):
            with open(paths["spec"], "w", encoding="utf-8") as f:
                f.write(
                    f"# Architecture & Contract Spec: {slug}\n\n"
                    f"## Problem & Users\n- {goal}\n\n"
                    f"## Functional Requirements\n- \n\n"
                    f"## Explicit Non-Goals\n- \n\n"
                    f"## Architecture & Module Contracts\n- \n\n"
                    f"## Data Models & Invariants\n- \n\n"
                    f"## Verified Tech Stack\n- (Verify real versions and APIs before coding)\n\n"
                    f"## Acceptance Criteria\n- [ ] \n"
                )
            created.append("spec.md")
        if not os.path.exists(paths["tasks"]):
            with open(paths["tasks"], "w", encoding="utf-8") as f:
                f.write(
                    f"# Vertical Slice Plan: {slug}\n\n"
                    f"| ID | Slice | Owned Paths | Verification Command | Status |\n"
                    f"|---|---|---|---|---|\n"
                    f"| T1 | Walking skeleton + build/test harness | | | pending |\n"
                )
            created.append("tasks.md")
    elif mode == "research":
        os.makedirs(paths["notes"], exist_ok=True)
        if not os.path.exists(paths["plan"]):
            with open(paths["plan"], "w", encoding="utf-8") as f:
                f.write(
                    f"# Research Plan: {slug}\n\n"
                    f"- **Question:** {goal}\n"
                    f"- **Audience & Scope:** \n"
                    f"- **Citation Style:** APA 7 (or `.verisource` setting)\n\n"
                    f"## Sub-Questions\n"
                    f"| ID | Sub-Question | Output File | Status |\n"
                    f"|---|---|---|---|\n"
                    f"| Q1 | | notes/q1.md | pending |\n\n"
                    f"## Source Strategy\n"
                    f"- Follow Verisource credibility tiers (Tier 1 primary/peer-reviewed first; open actual pages; verify DOIs).\n"
                )
            created.append("plan.md")
    return created


def ensure_gitignore(root: str) -> bool:
    if not os.path.exists(os.path.join(root, ".git")):
        return False
    gi = os.path.join(root, ".gitignore")
    lines = []
    if os.path.isfile(gi):
        with open(gi, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    if any(line.strip().rstrip("/") == ".overclock" for line in lines):
        return False
    with open(gi, "a", encoding="utf-8") as f:
        if lines and lines[-1] != "":
            f.write("\n")
        f.write(".overclock/\n")
    return True


def parse_state_fields(text: str) -> dict:
    fields = {}
    for line in text.splitlines():
        if ":" in line and not line.startswith("#"):
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields


def update_state_fields(state_path: str, updates: dict) -> str:
    with open(state_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    seen = set()
    new_lines = []
    for line in lines:
        replaced = False
        for key, val in updates.items():
            if line.startswith(f"{key}:"):
                new_lines.append(f"{key}: {val}")
                seen.add(key)
                replaced = True
                break
        if not replaced:
            new_lines.append(line)
    for key, val in updates.items():
        if key not in seen:
            new_lines.append(f"{key}: {val}")
    text = "\n".join(new_lines) + "\n"
    with open(state_path, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def get_active_slug(root: str):
    active_file = os.path.join(root, ".overclock", "active")
    if not os.path.isfile(active_file):
        return None
    with open(active_file, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    if not raw:
        return None
    try:
        return sanitize_slug(raw)
    except ValueError:
        return None


def validate_state_text(text: str) -> tuple:
    lines = text.splitlines()
    line_count = len(lines)
    char_count = len(text)
    errors = []
    for req in REQUIRED_STATE_FIELDS:
        if not any(line.startswith(req) for line in lines):
            errors.append(f"missing required field '{req}'")
    if line_count > MAX_STATE_LINES:
        errors.append(f"too many lines ({line_count} > {MAX_STATE_LINES})")
    if char_count > MAX_STATE_CHARS:
        errors.append(f"too many chars ({char_count} > {MAX_STATE_CHARS})")
    return line_count, char_count, errors


def cmd_init(args) -> int:
    try:
        slug = sanitize_slug(args.slug)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    root = find_workspace_root(args.cwd)
    paths = project_paths(root, slug)
    if os.path.exists(paths["base"]) and not args.force:
        print(f"error: project '{slug}' already exists at {paths['base']} (use --force to overwrite)", file=sys.stderr)
        return 1
    os.makedirs(paths["work"], exist_ok=True)
    with open(paths["brief"], "w", encoding="utf-8") as f:
        f.write(render_brief(slug, args.mode, args.goal))
    with open(paths["state"], "w", encoding="utf-8") as f:
        f.write(render_state(slug, args.mode, args.goal, status="active"))
    with open(paths["decisions"], "w", encoding="utf-8") as f:
        f.write(render_decisions(slug, args.mode))
    scaffold_mode_files(paths, slug, args.mode, args.goal)
    with open(paths["active_file"], "w", encoding="utf-8") as f:
        f.write(slug + "\n")
    gi_added = ensure_gitignore(root) if args.gitignore else False
    print(f"Initialized deepwork project '{slug}' ({args.mode}) at {paths['base']}")
    if gi_added:
        print(f"Added .overclock/ to {os.path.join(root, '.gitignore')}")
    return 0


def cmd_status(args) -> int:
    root = find_workspace_root(args.cwd)
    active = get_active_slug(root)
    projects_dir = os.path.join(root, ".overclock", "projects")
    projects = []
    if os.path.isdir(projects_dir):
        for name in sorted(os.listdir(projects_dir)):
            st_path = os.path.join(projects_dir, name, "state.md")
            if not os.path.isfile(st_path):
                continue
            text = open(st_path, encoding="utf-8").read()
            fields = parse_state_fields(text)
            lines, chars, errs = validate_state_text(text)
            projects.append({
                "slug": name,
                "active_marker": name == active,
                "status": fields.get("Status", "unknown"),
                "mode": fields.get("Mode", "unknown"),
                "phase": fields.get("Phase", ""),
                "lines": lines,
                "chars": chars,
                "budget_ok": not errs,
                "errors": errs,
                "path": os.path.join(projects_dir, name),
            })
    active_info = next((p for p in projects if p["slug"] == active), None) if active else None
    if args.json:
        print(json.dumps({"root": root, "active": active, "active_project": active_info, "projects": projects}, indent=2))
        return 0
    print(f"Workspace root: {root}")
    if active_info:
        budget = "OK" if active_info["budget_ok"] else "OVER BUDGET: " + "; ".join(active_info["errors"])
        print(f"Active project: {active_info['slug']} (mode={active_info['mode']}, status={active_info['status']}, {active_info['lines']} lines / {active_info['chars']} chars, {budget})")
        print(f"Path: {active_info['path']}")
    elif active:
        print(f"Active marker '{active}' points to missing state.md")
    else:
        print("Active project: none")
    if projects:
        print("All projects:")
        for p in projects:
            mark = "*" if p["active_marker"] else " "
            print(f"  {mark} {p['slug']} [{p['mode']}] ({p['status']})")
    return 0


def cmd_resume(args) -> int:
    try:
        slug = sanitize_slug(args.slug)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    root = find_workspace_root(args.cwd)
    paths = project_paths(root, slug)
    if not os.path.isfile(paths["state"]):
        print(f"error: project '{slug}' not found at {paths['base']}", file=sys.stderr)
        return 1
    text = update_state_fields(paths["state"], {"Status": "active", "Updated": now_str()})
    os.makedirs(paths["overclock"], exist_ok=True)
    with open(paths["active_file"], "w", encoding="utf-8") as f:
        f.write(slug + "\n")
    print(text, end="")
    return 0


def cmd_switch_mode(args) -> int:
    root = find_workspace_root(args.cwd)
    slug = get_active_slug(root)
    if not slug:
        print("error: no active project in workspace", file=sys.stderr)
        return 1
    paths = project_paths(root, slug)
    if not os.path.isfile(paths["state"]):
        print(f"error: state.md missing for active project '{slug}'", file=sys.stderr)
        return 1
    text = open(paths["state"], encoding="utf-8").read()
    fields = parse_state_fields(text)
    old_mode = fields.get("Mode", "unknown")
    goal = fields.get("Goal", slug)
    update_state_fields(paths["state"], {"Mode": args.mode, "Updated": now_str()})
    created = scaffold_mode_files(paths, slug, args.mode, goal)
    if os.path.isfile(paths["decisions"]):
        with open(paths["decisions"], "a", encoding="utf-8") as f:
            f.write(f"| {now_str()} | mode-switch | Switched `{old_mode}` -> `{args.mode}` | Transitioned phase inside `{slug}` |\n")
    print(f"Switched '{slug}' from '{old_mode}' to '{args.mode}'" + (f" (created: {', '.join(created)})" if created else ""))
    return 0


def cmd_stop(args) -> int:
    root = find_workspace_root(args.cwd)
    slug = get_active_slug(root)
    status_val = "paused"
    if args.complete:
        status_val = "completed"
    elif args.archive:
        status_val = "archived"
    active_file = os.path.join(root, ".overclock", "active")
    if not slug:
        if os.path.isfile(active_file):
            os.remove(active_file)
        print("No active deepwork project.")
        return 0
    paths = project_paths(root, slug)
    if os.path.isfile(paths["state"]):
        update_state_fields(paths["state"], {"Status": status_val, "Updated": now_str()})
    if os.path.isfile(paths["active_file"]):
        os.remove(paths["active_file"])
    print(f"Stopped deepwork project '{slug}' (Status: {status_val}). Hooks are now silent.")
    return 0


def cmd_check_state(args) -> int:
    root = find_workspace_root(args.cwd)
    slug = get_active_slug(root)
    if not slug:
        print("error: no active project in workspace", file=sys.stderr)
        return 1
    paths = project_paths(root, slug)
    if not os.path.isfile(paths["state"]):
        print(f"error: state.md missing at {paths['state']}", file=sys.stderr)
        return 1
    text = open(paths["state"], encoding="utf-8").read()
    lines, chars, errors = validate_state_text(text)
    if errors:
        print(
            f"state.md check FAILED ({lines}/{MAX_STATE_LINES} lines, {chars}/{MAX_STATE_CHARS} chars): "
            + "; ".join(errors)
            + ". Trim old completed items/details into lab.md, tasks.md, or decisions.md.",
            file=sys.stderr,
        )
        return 1
    print(f"state.md check OK ({lines}/{MAX_STATE_LINES} lines, {chars}/{MAX_STATE_CHARS} chars)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="project.py", description="Manage overclock Deepwork project state.")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize a new deepwork project and mark it active.")
    p_init.add_argument("slug", help="Lowercase kebab-case project identifier")
    p_init.add_argument("--mode", required=True, choices=MODES)
    p_init.add_argument("--goal", required=True)
    p_init.add_argument("--cwd", default=os.getcwd())
    p_init.add_argument("--gitignore", action="store_true")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_st = sub.add_parser("status", help="Show active project and list projects.")
    p_st.add_argument("--cwd", default=os.getcwd())
    p_st.add_argument("--json", action="store_true")
    p_st.set_defaults(func=cmd_status)

    p_res = sub.add_parser("resume", help="Activate an existing project.")
    p_res.add_argument("slug")
    p_res.add_argument("--cwd", default=os.getcwd())
    p_res.set_defaults(func=cmd_resume)

    p_sw = sub.add_parser("switch-mode", help="Switch active project mode while preserving files.")
    p_sw.add_argument("mode", choices=MODES)
    p_sw.add_argument("--cwd", default=os.getcwd())
    p_sw.set_defaults(func=cmd_switch_mode)

    p_stop = sub.add_parser("stop", help="Clear .overclock/active and update project status.")
    grp = p_stop.add_mutually_exclusive_group()
    grp.add_argument("--pause", action="store_true")
    grp.add_argument("--complete", action="store_true")
    grp.add_argument("--archive", action="store_true")
    p_stop.add_argument("--cwd", default=os.getcwd())
    p_stop.set_defaults(func=cmd_stop)

    p_chk = sub.add_parser("check-state", help="Verify active state.md stays within line/char budget.")
    p_chk.add_argument("--cwd", default=os.getcwd())
    p_chk.set_defaults(func=cmd_check_state)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
