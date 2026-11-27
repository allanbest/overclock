# Mode Playbook: Build (Serious Software & Applications)

Build production-grade software through locked module contracts, small vertical slices, real automated verification, and disciplined root-cause debugging.

## The Iterative Engineering Loop

### 1. Architecture & Contract Spec (`spec.md`)
Keep `spec.md` tight (1–2 pages) and settle it before writing substantial code:
- **Problem, Requirements & Explicit Non-Goals:** state what is intentionally out of scope.
- **Module Boundaries & Contracts:** public APIs, CLI/HTTP schemas, types, and ownership boundaries.
- **Data Models & Invariants:** persistence schema, state transitions, and invariants that must never break.
- **Verified Tech Stack:** verify real installed versions, APIs, and docs before coding (never hallucinate library methods or flags — check installed packages or docs via `verification.md`).
- **Acceptance Criteria:** concrete, testable checkboxes (`- [ ] ...`).

For large builds, briefly confirm `spec.md` with the user before starting `T1`.

### 2. Vertical Slice Plan (`tasks.md`)
Break the spec into ordered, end-to-end increments (`T1`, `T2`, ...):
- **`T1` is always the Walking Skeleton:** minimal runnable project layout, shared types/interfaces, build/typecheck, and a passing smoke test.
- Every task row MUST specify **Owned Paths** and an exact **Verification Command**.
- Prefer small, testable slices over building whole horizontal layers blindly.

### 3. Build Loop (Adaptive Serial vs. Parallel Waves)
- **Default — Serial Vertical Slices:** implement one slice at a time when modules share state or types. One context holding the full picture is cheaper and produces fewer integration bugs.
- **Parallel Module Waves (Only After `T1` Locks Interfaces):** when 2–4 tasks in `tasks.md` have **strictly disjoint file ownership** against locked contracts (e.g., `src/storage/`, `src/api/`, `src/ui/`, `tests/fixtures/`), dispatch them in parallel via [../../orchestrate/SKILL.md](../../orchestrate/SKILL.md):
  - *Antigravity*: `invoke_subagent` (`self`, `Workspace: "share"`) so each worker edits in an isolated worktree without clobbering sibling edits, then merge cleanly.
  - *Claude Code*: `overclock:worker` with explicit non-overlapping `You own:` paths.
  - Integrate and run the combined test suite serially after each wave.

### 4. Real Verification (Never "Looks Right")
A slice is NOT done until its verification command passes after your final edit:
- Run unit/integration tests, typecheck/lint, and build.
- For apps/services/UIs, run a real smoke test (CLI execution, local server health/API roundtrip, or Playwright / Antigravity `browser` subagent check for rendered UI & console errors).
- Record only observed passing commands and counts.

### 5. Reflect & Fix — 2-Failure Anti-Thrashing Rule
If the **same error or failing test happens twice in a row**:
1. **STOP** patching symptoms or guessing fixes.
2. Write a 3-line **root-cause hypothesis** (what state/assumption is actually wrong).
3. Run a minimal targeted probe (print/inspect real runtime state, minimal repro, or read the actual failing dependency code).
4. Apply the clean structural fix and verify.
5. Log non-obvious root causes, workarounds, and architecture choices in `decisions.md`.

### 6. Milestone Checkpoints & Final Spec Audit
- Update `tasks.md` and `state.md` after each slice; run `python3 ../scripts/project.py check-state` (or relative path). Suggest a fresh chat at major milestones.
- Before declaring the software done:
  1. Run the **full** test suite, linter/typechecker, and clean build.
  2. Walk every checkbox in `spec.md` (`Acceptance Criteria`) and match it to observed passing evidence.
  3. Optionally run 1 fresh-context verifier worker (see `verification.md`) to audit the repo against `spec.md`.
