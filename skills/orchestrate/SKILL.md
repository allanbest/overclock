---
name: orchestrate
description: Run a large, splittable job with several helper agents while using as little of the usage limit as possible. Use when the user asks for "multi-agent", "parallel agents", "split this up", "use subagents", or gives a job with clearly separate parts (research several topics, review many files or folders, compare several options, update several independent modules), or when a Deepwork phase benefits from parallel sub-questions, sweeps, or disjoint module waves. Starts by deciding whether splitting is worth it at all.
---

# Orchestrate (budget-aware multi-agent work)

Multi-agent work is powerful but expensive: Anthropic measured multi-agent setups at about 15× the tokens of a normal chat. Every helper starts from zero and holds a separate context cache. Splitting pays off only when parts are genuinely independent and each is substantial.

## 1. Decide whether to split

**Do NOT split** (do it serially yourself, or use a single cheap lookup helper) when:
- the whole job needs fewer than about 10 tool calls,
- the parts depend tightly on each other or share deep reasoning (most single-feature coding, mathematical proofs, core hypothesis reasoning in `science` mode), or
- two helpers would need to edit the same files.

**Split** when there are 2–5 independent parts, each needing real work (literature sub-questions, orthogonal ablation/seed sweeps, or disjoint software modules after interfaces are locked). If you decide not to split, say so in one line and do the work directly.

## 2. Plan in a file

Check whether `.overclock/active` exists in the workspace root:
- **If a Deepwork project is active**, store the plan and worker outputs inside `.overclock/projects/<slug>/work/` (or `notes/` for `research`, `experiments/` for `science`).
- **Otherwise**, create `.overclock/plan.md` and write outputs to `.overclock/work/` (add `.overclock/` to `.gitignore` if appropriate).

```markdown
# Plan: <job>
Goal: <one line>
| # | Part | Helper / Model | Owns (files/areas) | Output file |
|---|------|----------------|--------------------|-------------|
| 1 | ...  | worker (sonnet / flash / share) | src/billing/ | .../work/1-billing.md |
Final check: <what to verify and how>
```

- **Strict disjoint ownership:** no two helpers own the same files or the same question.
- **Cap at 5 helpers** (usually 2–4 is optimal).

## 3. Platform dispatch table

| Need | Claude Code | Antigravity |
|---|---|---|
| Fast read-only codebase/file search | `overclock:scout` (`haiku`) | `invoke_subagent` (`research`, `Model: "flash_lite"` or `"flash"`) |
| Research / analysis / verification | `overclock:worker` (`sonnet`) | `invoke_subagent` (`self`, `Model: "flash"`, or `research` if local-only) |
| Parallel disjoint code edits | `overclock:worker` (`sonnet`, disjoint `You own:`) | `invoke_subagent` (`self`, `Workspace: "share"` for isolated worktrees) |
| Wide homogeneous fan-out (4+ items) | Batch `overclock:worker` calls | `run_workflow` script or batched `invoke_subagent` |

## 4. Launch helpers in parallel

Launch all independent helpers in **one turn** with self-contained prompts (point to files rather than pasting large text):

```text
Part <#> of <job>. Goal of the whole job: <one line>.
Your part: <exact scope and question>.
You own: <files/areas>; do not edit anything else.
Context you need: <only the essential paths, locked contracts, or constraints>.
Sourcing rule: verify external claims/APIs against primary sources (apply Verisource rules if available); never invent URLs, DOIs, or APIs; mark unchecked items `❓ Unverified`.
Write full results to: <output file path>
Reply under 150 words with: Status, Result, Details path, Files changed, Open issues.
```

## 5. Combine, verify once, and clean up

- Read the short replies first; open a helper's output file only for parts you actually need.
- If one helper reports `partial` or `blocked`, fix it yourself or relaunch only that piece.
- Integrate edits cleanly (merge worktrees if using Antigravity `Workspace: "share"`), then run **one** verification pass at the end (full test/build for code, load-bearing source check for research, or fresh-seed/skeptical check for science).
- Report the result concisely and link any kept artifacts. Clean up scratch files under `work/` that are no longer needed.

## Avoid

- Splitting small or tightly coupled work.
- Helper-to-helper chatter or "agent teams".
- Pasting large file contents into prompts; pass file paths instead.
- Reviewing every helper's output with another helper.
