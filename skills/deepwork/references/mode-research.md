# Mode Playbook: Research (Multi-Source Web & Literature Synthesis)

Combine parallel worker throughput with Verisource anti-hallucination rigor to produce verified, traceable reports without inflating the main context window.

## The Iterative Research Loop

### 1. Decompose (`plan.md`)
- Frame the core research question, audience, scope boundaries, and citation style (check `.verisource` / user preference; default APA 7 for formal reports, inline links for informal briefs).
- Split into **3–5 non-overlapping sub-questions** (`Q1`..`Q5`) in `plan.md`, each mapped to `notes/q<n>-<slug>.md`.

### 2. Parallel Cheap Gatherers
Follow [../../orchestrate/SKILL.md](../../orchestrate/SKILL.md) to launch 2–4 parallel workers (1 sub-question each):
- *Claude Code*: `overclock:worker` (or `overclock:scout` for quick factual lookups).
- *Antigravity*: `research` subagent with `Model: "flash"` (note: Antigravity's `research` runs in a read-only no-network sandbox when local; if live web search is needed on Antigravity, keep web searches in the main session or use `self` / `browser` as appropriate).
- Every worker MUST enforce [verification.md](verification.md) / Verisource rules:
  - Open actual pages rather than relying on snippets.
  - Rate sources by credibility tier (Tier 1 primary/peer-reviewed, Tier 2 reputable orgs/news, Tier 3 leads only).
  - Trace derivative articles back to the primary source; count syndications as 1 source.
  - Verify DOIs/paper metadata before citing; never invent URLs or quotes.
  - Write full findings and URLs to `notes/q<n>-<slug>.md` and return <=150 words.

### 3. Reflect & Fill Gaps
- Read worker short summaries first; open `notes/` files only where details matter.
- Identify contradictions, missing primary sources, or claims backed only by Tier 3 sources.
- Update `plan.md` and run targeted follow-up checks only for the remaining gaps (do not re-run everything).

### 4. Load-Bearing Verification
Before drafting the final report, independently re-verify the **3–5 load-bearing claims** that the main conclusion depends on:
- Confirm exact numbers, dates, units, population, and quote wording in the original source.
- Check DOIs with Verisource's `cite_doi.py` (if installed) or `https://citation.doi.org/format?doi=<doi>&style=<style>&lang=en-US`.

### 5. Synthesize (`report.md`)
Write `report.md` (and present a concise executive answer to the user):
- Lead with the direct conclusion.
- Include a compact **Fact-Check Table** marking key claims `✅ Verified`, `⚠️ Disputed / Partial`, `❌ Contradicted`, or `❓ Unverified`.
- Explicitly label reasoning beyond the sources as `[Inference]` or `[Conjecture]`.
- Include a formatted References section using only details observed in the sources.
