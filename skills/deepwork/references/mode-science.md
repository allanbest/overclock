# Mode Playbook: Science (ML, Physics, Math, Empirical R&D)

Keep reasoning **mostly serial in one head** so mathematical, physical, and experimental context stays coherent. Use `lab.md` as long-term memory so dead ends are never repeated across cycles or fresh sessions.

## The Iterative Scientific Loop

### 1. Propose & Ground
- Clarify the objective, constraints (compute, data, tolerances, runtime), and baseline success metric in `brief.md`.
- If grounding against prior papers, theorems, or SOTA numbers, verify every external reference via [verification.md](verification.md) (or the Verisource `fact-check` skill). Never invent citations or baseline scores.

### 2. Mandatory Baseline First
- Before testing any novel idea, build and run the simplest working baseline (or toy/analytical limiting case).
- Log the exact command, seed, dataset/parameters, and raw metric in `lab.md` under `E1 — Baseline`.

### 3. Falsifiable Hypothesis Protocol (`H#`)
**Before** running an experiment or proof attempt, add a row to `lab.md` (`Hypothesis Registry`):
- **Mechanism:** *why* the change or lemma should hold.
- **Quantitative Prediction / Formal Statement:** exact expected effect or theorem statement.
- **Falsification / Kill Condition:** what concrete result refutes `H#` or triggers stopping.
- **Minimal Discriminating Test:** smallest experiment/derivation that separates `H#` from the null hypothesis.

Never move goalposts after seeing the output.

### 4. Execute & Record (`E#`)
- Put each experiment's script, config, and summary output under `experiments/E<n>/` so every result is reproducible.
- Run commands cleanly (on Claude Code, `overclock` trims noisy stdout while preserving errors and saving the full log path).
- Log in `lab.md`: hypothesis ID, exact command, raw quantitative metrics vs. baseline, and any anomalies.

### 5. Tactical Multi-Agent Fan-Out (Only When Orthogonal)
Never split a single tightly-coupled proof or debugging chain across helpers. Split only via [../../orchestrate/SKILL.md](../../orchestrate/SKILL.md) for:
1. **Parallel literature / baseline grounding:** 2–3 cheap helpers search independent subtopics and write to `notes/lit-*.md`.
2. **Independent ablations / parameter / seed sweeps:** 2–4 helpers run disjoint configs in separate `experiments/E*/` directories; the main session aggregates results into `lab.md`.
3. **Fresh-context skeptical verifier:** 1 independent helper audits the final claim (see `verification.md`).

### 6. Reflect, Domain Audit & Dead-End Graveyard
After each `E#`, ask *why* it behaved that way before proposing `H<n+1>`. Apply the matching sanity checklist:

- **ML / Data Science:** check train/val/test leakage, target leakage, seed variance (>=3 seeds for main claims), identical hyperparameter/compute budget for baselines, silent NaNs/shape broadcasts, and metric vs. objective mismatch.
- **Physics / Simulation:** check dimensional analysis and units, conservation laws (energy, mass, momentum, probability), limiting cases ($x \to 0$, $x \to \infty$, zero coupling), grid/timestep convergence, and numerical stability.
- **Math / Formal Reasoning:** check boundary cases ($n=0, 1$, empty/degenerate objects), hidden assumptions (continuity, convexity, independence, invertibility), dual/contradiction checks, and write a fast randomized Python counterexample script before investing in a long proof.

**Dead-End Graveyard:** whenever an approach is refuted or hits a structural wall, log it in `lab.md` (`## Dead Ends & Refuted Approaches`) AND summarize it in `state.md` (`Dead Ends / Avoid:`) so neither you nor a future session retries it without new evidence.

### 7. Independent Verification Gate
Before declaring a finding confirmed:
- Reproduce on an independent check (fresh random seed, held-out split, finer grid/timestep, or independent derivation).
- Tag every claim in your final report (`[Observed]`, `[Derived]`, `[Verified Source ✅]`, or `[Conjecture]`).
- For high-stakes claims, run 1 fresh-context skeptical verifier pass from `verification.md`.
