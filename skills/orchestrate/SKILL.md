---
name: orchestrate
description: Run a large, splittable job with several helper agents while using as little of the usage limit as possible. Use when the user asks for "multi-agent", "parallel agents", "split this up", "use subagents", or gives a job with clearly separate parts (research several topics, review many files or folders, compare several options, update several independent modules). Starts by deciding whether splitting is worth it at all.
---

# Orchestrate (cheap multi-agent work)

Multi-agent work is powerful but expensive: Anthropic measured multi-agent setups at about 15× the tokens of a normal chat. Every helper starts from zero, re-reads whatever it needs, and its cache is separate from yours. Splitting pays off only when the parts are truly independent and each is big. Your job here is to get the benefit while keeping the usage cost down.

## 1. Decide whether to split

Don't split (do it yourself, or use a single `overclock:scout`) when:
- the whole job needs fewer than about 10 tool calls, or
- the parts depend on each other or share a lot of context (most single-feature coding work: one person holding the whole picture is cheaper and better), or
- the parts would edit the same files.

Split when there are 2–5 parts that are independent, each needing real work (many reads, searches or edits). If you decide not to split, say so in one line and just do the work.

## 2. Plan in a file

Create `.overclock/plan.md` in the working folder (add `.overclock/` to `.gitignore` if it's a git repo):

```markdown
# Plan: <job>
Goal: <one line>
| # | Part | Agent | Model | Owns (files/areas) | Output file |
|---|------|-------|-------|--------------------|-------------|
| 1 | ...  | worker | sonnet | src/billing/ | .overclock/work/1-billing.md |
Final check: <what to verify and how>
```

- **Give each part a separate scope.** No two helpers own the same files or the same question, so nothing is explored twice.
- **Use at most 5 helpers.** Usually 2–4 is right.
- **Pick the cheapest model that can do the part:**
  - `overclock:scout` (Haiku): finding things, listing, simple lookups.
  - `overclock:worker` (Sonnet): analysis, research, writing or changing code.
  - Override the model only if a part is unusually hard. Never use the most expensive model by default.

## 3. Launch the helpers

Launch all independent helpers in **one message**, so they run in parallel. Each prompt must stand on its own, because helpers can't see this conversation:

```
Part <#> of <job>. Goal of the whole job: <one line>.
Your part: <exact scope and question>.
You own: <files/areas>; don't edit anything else.
Context you need: <only the facts this part needs: paths, decisions, constraints>.
Write full results to: .overclock/work/<#>-<name>.md
Reply in your standard short format.
```

Keep the context section short. Point to files rather than pasting their contents.

## 4. Combine the results

- Read the short replies first. Open a helper's output file only for the parts you actually need. That's the point of keeping the bulk in files.
- If a helper reports `partial` or `blocked`, fix it yourself or relaunch only that part with a sharper prompt. Don't rerun everything.
- Write the combined answer or finish the integration yourself.

## 5. One final check

Run a single check at the end, not a review after every step:
- for code: run the tests or build once;
- for research: check the 2–3 claims the conclusion depends on most;
- if a separate check is really needed, launch one `overclock:worker` with a precise checklist.

## 6. Report and clean up

Tell the user the result. Mention briefly how the work was split (one line), and give the paths of any detailed output files worth keeping. Delete `.overclock/work/` files that aren't needed any more, unless the user wants them.

## Avoid

- Splitting a small or tightly connected job.
- Helpers that discuss with each other, or "agent teams". Claude's agent-teams feature is experimental and can use roughly 7× the tokens.
- Pasting large text into helper prompts; point to files instead.
- Reviewing every helper's output with another helper.
- Re-reading everything a helper already summarized.
