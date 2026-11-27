---
name: deepwork
description: Run long-horizon iterative research, scientific/ML/physics/math inquiry (proposals, baselines, falsifiable hypotheses, experiments, proofs), serious multi-milestone software building (spec, vertical slices, tests, reflect/fix), or multi-source deep research projects. Use when the user asks to start or resume a research project, run experiments, prove a result, build a full app or multi-module system, or invokes /overclock:deepwork. Do not use for quick questions or single-file fixes.
---

# Deepwork

Structured, disk-backed long-horizon work across three modes (`science`, `build`, `research`) on one shared `.overclock/projects/<slug>/` core.

## 1. Light Path Gate

Before creating any files, check whether the task actually needs a project loop. If it is a quick question, a small single-file edit, or solvable in under ~10 tool calls, **answer directly** and do not initialize `.overclock/projects/`.

## 2. Start or Resume

1. Check existing workspace state (relative to this skill's directory):
   `python3 scripts/project.py status`
2. **If resuming an existing project**: read its `state.md` and current mode file (`lab.md`, `spec.md` + `tasks.md`, or `plan.md`), confirm the next step in one line, and continue.
3. **If starting a new project**:
   - Ask at most 1–3 crisp clarifying questions only if goal, constraints, or acceptance criteria are genuinely ambiguous.
   - Pick the initial mode:
     - `science`: ML experiments, physics/simulations, math proofs, empirical R&D
     - `build`: serious software, services, libraries, CLI tools, or full apps
     - `research`: deep web, literature, or competitive analysis
   - Initialize the workspace (add `--gitignore` if in a git repo and the user wants local-only notebooks):
     `python3 scripts/project.py init <slug> --mode <science|build|research> --goal "<one-line goal>"`

## 3. Load Only the Active Mode Playbook

Read **only** the single playbook matching the active mode (plus `references/verification.md` before citing external claims or running final verification):

- **Science** (`science`): [references/mode-science.md](references/mode-science.md)
- **Build** (`build`): [references/mode-build.md](references/mode-build.md)
- **Research** (`research`): [references/mode-research.md](references/mode-research.md)
- **Verification & Verisource**: [references/verification.md](references/verification.md)

Whenever splitting independent work across parallel helpers, also read [../orchestrate/SKILL.md](../orchestrate/SKILL.md).

## 4. Shared Loop Discipline & Token Efficiency

- **Keep `state.md` tiny (<=25 lines, <=1,800 chars):** update `Phase`, `Active`, `Completed`, `Dead Ends / Avoid`, `Next Step`, and `Key Files` at the end of every cycle or slice, then run:
  `python3 scripts/project.py check-state`
- **Mode transitions inside one project:** if a project evolves (`research` -> `science` -> `build`), preserve all history in the same folder via:
  `python3 scripts/project.py switch-mode <mode>`
- **Fresh-session rhythm:** at major milestone boundaries, every 3–5 experiment cycles, or whenever context grows heavy, update `state.md` and `decisions.md` (or run `/overclock:reflect`) and suggest continuing in a fresh chat (`/clear` or a new session). `SessionStart` reloads `state.md` automatically on both Claude Code and Antigravity.
- **Cross-platform helper dispatch:**
  - *Claude Code*: `overclock:scout` (Haiku) for read-only discovery; `overclock:worker` (Sonnet) for scoped work.
  - *Antigravity*: `research` subagent (`flash_lite`/`flash`) for discovery/lit search; `self` (`Workspace: "share"`) for parallel disjoint code edits; `run_workflow` for wide homogeneous fan-outs.

## 5. Finishing

Run the active mode's final verification gate, present results with explicit evidence tags from `references/verification.md`, and remind the user to run `/overclock:stop` when done so project hooks return to zero-token silence.
