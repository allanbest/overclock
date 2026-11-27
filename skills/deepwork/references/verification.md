# Verification & Verisource Integration

Use consistent epistemic standards across `science`, `build`, and `research` modes so unverified assumptions never masquerade as proven facts.

## Epistemic Status Tags

Use these exact tags in `lab.md`, `report.md`, and final user summaries:
- `[Observed]` — directly measured from a command, test, or experiment run you observed in this session (state exact command/seed).
- `[Derived]` — mathematically or logically proved/checked from verified premises or code read directly.
- `✅ Verified` — external factual claim backed by a Tier 1 primary source or two independent Tier 2 sources.
- `⚠️ Disputed / Partial` — credible sources conflict, or only Tier 3 / partial support exists.
- `❌ Contradicted` — credible primary sources or tests refute the claim.
- `❓ Unverified` — could not verify (missing source, offline, or unexecuted check). Never guess to fill this gap.
- `[Conjecture]` — working hypothesis or inference beyond direct evidence.

## Verisource Integration (and Standalone Fallback)

- **When Verisource (`fact-check` skill) is installed:** invoke/follow `fact-check` whenever verifying external statistics, historical/scientific claims, literature baselines, or building bibliographies (`cite_doi.py`).
- **Standalone fallback (if Verisource is not installed):**
  1. **Tier 1 (strong):** peer-reviewed papers, government/intergovernmental data, official docs/specs, primary code/datasets.
  2. **Tier 2 (good):** university pages, recognized standards/expert bodies, established outlets with corrections policies.
  3. **Tier 3 (leads only):** preprints (explicitly note not peer-reviewed), expert blogs, Wikipedia (follow references to Tier 1–2).
  4. **Reject:** anonymous SEO/content farms, forums/social posts as final evidence, sites selling what they review.
  5. **Independence & exactness:** five outlets repeating one press release count as one source; match exact numbers, units, and dates; check DOIs via `https://citation.doi.org/format?doi=<doi>&style=apa&lang=en-US` before citing; never fabricate a URL, DOI, or library API.

## Fresh-Context Skeptical Verifier Template

At the end of a major `science` result or `build` milestone, spawn **1** fresh-context worker with zero prior conversation history using this prompt:

```text
You are an independent skeptical verifier. Your job is to try to falsify or find gaps in the work below — not rubber-stamp it.
Project folder: .overclock/projects/<slug>/
Mode: <science|build>
Read: <lab.md + target experiment scripts OR spec.md + tasks.md>
Checks to run:
- For science: re-run the claim on a fresh seed / edge case / independent check; inspect for data leakage, unit errors, or hidden assumptions.
- For build: run the full test suite and build; check every Acceptance Criterion in spec.md against actual code and observed output.
Write findings to: .overclock/projects/<slug>/work/verify-final.md
Reply in <=150 words with: Verdict (PASS / FAIL / PARTIAL), exact commands run, and any counterexamples or unmet criteria.
```
