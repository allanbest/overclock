---
name: reflect
description: Pause an active Deepwork project to audit progress, diagnose repeated failures via root-cause analysis, verify claims or spec alignment, log dead ends and decisions, and compact state.md for a fresh session. Use when the user invokes /overclock:reflect, hits a recurring bug/blocker, finishes a major milestone, or wants to review before continuing in a new chat.
---

# Reflect

Structured mid-project checkpoint and root-cause reset for an active Deepwork project.

## Steps

1. Inspect the active project (path relative to `skills/deepwork/`):
   `python3 ../deepwork/scripts/project.py status`
   If no project is active, check whether a standalone `HANDOFF.md` is wanted instead (`../handoff/SKILL.md`).
2. Read `state.md`, `decisions.md`, and the active mode file (`lab.md`, `spec.md` + `tasks.md`, or `plan.md`).
3. Run the mode-appropriate audit:
   - **`science`:** check whether hypotheses had pre-registered falsification criteria, move refuted approaches into `Dead Ends & Refuted Approaches`, run the domain sanity checklist (leakage/seeds, units/limits, edge cases/counterexamples), and verify external citations.
   - **`build`:** if any error failed twice, enforce the **2-Failure Anti-Thrashing Rule** (write root-cause hypothesis, run minimal probe, fix cause not symptom); verify `tasks.md` status reflects actually passing test commands and matches `spec.md` contracts.
   - **`research`:** check for Tier-3-only or conflicting claims, confirm load-bearing facts against primary sources, and identify exact remaining gaps.
4. Record key architectural choices, pivots, and root-cause lessons in `decisions.md`.
5. Update `state.md` (keep it <=25 lines / <=1,800 chars: `Phase`, `Active`, `Completed`, `Dead Ends / Avoid`, `Next Step`, `Key Files`), then validate:
   `python3 ../deepwork/scripts/project.py check-state`
6. Summarize in a few bullets: what is verified, what dead ends were ruled out, the exact next step, and—if the conversation is getting long—recommend continuing in a fresh chat (`/clear` or new session), which will auto-load `state.md`.
