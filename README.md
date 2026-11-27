<p align="center"><img src="assets/icon.png" width="96" alt=""></p>

# overclock

**Token-efficient deep research, scientific experimentation, iterative software building, and budget-aware multi-agent orchestration — for Claude (Code & Cowork) and Antigravity.**

overclock v1.0 combines two complementary layers:
1. **Runtime token efficiency (Claude Code / Cowork):** trims noisy command output, injects tiny lean habits, blocks accidental cold-cache re-reads, and writes zero-LLM transcript checkpoints.
2. **Deepwork + Orchestrate (Claude Code, Cowork & Antigravity):** structured long-horizon workflows (`science`, `build`, `research`) with disk-backed project memory, falsifiable hypothesis/spec loops, Verisource anti-hallucination verification, and budget-aware multi-agent splitting — adding **0 tokens** when no project is active.

## Why this works

Each message re-sends the whole conversation to the model. Long logs, unfocused multi-agent fan-outs, and cold-cache session resumes burn context and subscription limits fast, while long scientific or software tasks lose track of dead ends and contracts across breaks. overclock keeps raw noise out of context and stores structured state (`state.md`, `lab.md`, `spec.md`, `tasks.md`, `decisions.md`) on disk so fresh sessions pick up cleanly.

## What's inside

### 1. Context & Token Efficiency (Claude Code / Cowork)

| Part | What it does |
|---|---|
| **Output trimmer** (hook) | When a command prints over ~6,000 characters, Claude gets a compact version: start, end, **every error/warning line** with context, and repeated lines collapsed (`[×3000]`). The full output stays in a log file whose path is included. Short outputs are never touched. |
| **Lean rules** (hook, ~150 tokens, once per session) | Lead with the answer, batch tool calls, read only needed line ranges, and trust trimmed output. |
| **`scout` & `worker`** (Claude subagents in `claude-agents/`) | `overclock:scout` (Haiku) for broad read-only lookups; `overclock:worker` (Sonnet) for scoped research/implementation writing full results to disk and returning <150 words. |
| **Checkpoint + auto-resume** (hooks) | At the end of every Claude turn, writes a ~1–2 KB transcript checkpoint (`~/.claude/overclock/checkpoints/<project>/`) with zero extra model calls. New chats (`/clear` or startup) load the newest checkpoint automatically. |
| **Idle-session warning** (hook) | Claude's cache of your conversation lasts about an hour. If you come back to a big conversation (60k+ tokens) after that, your next message re-processes the whole thing at full cost. overclock holds that message once, before any usage is spent, and points to `/clear` or a new chat (which picks up from the checkpoint). If you send it anyway twice in a row, it stops holding and shows a one-line note instead, until you next take the advice. |
| **Compaction guide** (hook) | Steers compaction summaries to keep goals, paths, unresolved errors, and active Deepwork dead ends. |

### 2. Deepwork & Multi-Agent Orchestration (Claude + Antigravity)

| Skill / Command | What it does |
|---|---|
| **`/overclock:deepwork`** | Entry point for long-horizon projects. Includes a **Light Path Gate** (simple questions answer directly with no files created) and routes into one of 3 modes on a shared `.overclock/projects/<slug>/` core. |
| **`/overclock:orchestrate`** | Budget-aware multi-agent splitter (checks if splitting beats serial work, caps at 2–5 helpers, enforces disjoint file ownership, stores details on disk, returns <=150 words). Dispatches natively to `overclock:scout`/`worker` on Claude Code and `research`/`self` (`Workspace: "share"`)/`run_workflow` on Antigravity. |
| **`/overclock:reflect`** | Mid-project audit: enforces the 2-failure root-cause reset, moves refuted attempts to dead ends, checks Verisource claims/spec alignment, and tightens `state.md` for a fresh session. |
| **`/overclock:handoff`** | Writes a compact ~300-word `HANDOFF.md` (and reminds to sync `state.md` if a Deepwork project is active). |
| **`/overclock:stop`** | Pauses, completes, or archives the active project and removes `.overclock/active` so session hooks return to 0-token silence. |

#### Deepwork Modes

| | 🧪 `science` (ML, physics, math) | 🛠️ `build` (serious software & apps) | 🌐 `research` (web & literature) |
|---|---|---|---|
| **Loop** | Propose -> Baseline -> Falsifiable Hypothesis -> Run/Derive -> Audit & Log Dead Ends -> Repeat | Architecture Spec -> Vertical Slice Plan -> Build -> Automated Test -> 2-Failure Reflect/Fix -> Repeat | Decompose -> Parallel Source Gathering -> Reflect & Fill Gaps -> Verify Key Claims -> Synthesize |
| **Key files** | `lab.md` + `experiments/` | `spec.md` + `tasks.md` | `plan.md` + `notes/` + `report.md` |
| **Parallelism** | Mostly serial in one head; helpers only for lit grounding, orthogonal sweeps, or final skeptical check | Serial walking skeleton (`T1`) + coupled slices; parallel waves only for disjoint modules with locked interfaces | 2–4 cheap parallel workers (1 sub-question each) |
| **Rigor & Anti-Hallucination** | Pre-registered kill criteria, domain sanity checklists (leakage, units/limits, counterexamples), dead-end graveyard | Real test/build/smoke verification, verified real library APIs, 2-failure root-cause rule, spec audit | Paired with [Verisource](https://github.com/allanbest/verisource) (`fact-check` skill) credibility tiers, DOI verification, and `✅`/`⚠️`/`❌`/`❓` labels |

Both Claude Code (`startup`, `clear`, `compact`) and Antigravity (`SessionStart`) automatically load the active project's compact `state.md` (<=25 lines / <=1,800 chars) when `.overclock/active` exists — and inject **0 tokens** when no project is active.

### 3. Model tiers (`/overclock:tier`)

A plugin can't add a new model to Claude's model picker, and switching the main chat's model mid-conversation throws away the cache (the whole chat is re-read at full price on the new model). So overclock routes work through **helpers** instead: pick a tier once, and every `overclock:scout` / `overclock:worker` call gets the right model.

| Tier | Priority | Main chat | Helpers | Advisor |
|---|---|---|---|---|
| `low` (default) | Save usage | Sonnet | Haiku for lookups, Sonnet for normal work, Opus only for the single hardest piece | off |
| `medium` | Balanced | Sonnet | Sonnet by default, Opus for hard reasoning, debugging and review, Haiku only for file search | off |
| `high` | Quality first | Opus | Opus for real work, Sonnet for routine offload, no Haiku | off |
| `extra` | Quality + Fable on the hardest parts | Opus | Sonnet routine, Opus default, Fable for architecture, stubborn bugs, proofs, final review | Fable |
| `max` | Best quality | Fable | Sonnet only for bulk, Opus and Fable for everything else | off |

`extra` and `max` are **off by default**, because on many plans Fable bills usage credits. Turn them on with `/overclock:tier fable on` if you have credits. overclock also checks for free whether Fable is listed for your account. Run `/overclock:tier` to see the options, `/overclock:tier medium` to set one, or `/overclock:tier off` to turn routing off; new chats load it automatically (about 250 tokens). Pick the recommended main-chat model with `/model` at the **start** of a chat.

**The advisor matters more than the helpers.** Claude Code's advisor setting (`advisorModel`, toggled with `/advisor`) sends the *whole conversation* to a stronger model several times per task. In a test with the advisor set to Fable, the advisor was ~70% of the cost. `/overclock:tier` tells you when your advisor setting doesn't match the tier, and the tier tells Claude how sparingly to call it.

## Measured results (v0.3.0 / v0.4.0 Claude Code benchmarks)

Real Claude Code sessions (Opus 5.5) with and without overclock, interleaved, 3–6 runs each, on 2026-11-24. Every answer was correct in both versions.

| Task | Without | With overclock | Change |
|---|---|---|---|
| Run a script with a 95 KB log, find the 3 warnings | $0.268 | $0.184 | **−31%** |
| Same with a 16 KB log | $0.230 | $0.187 | **−19%** |
| Find a value in a 30-file codebase | $0.166 | $0.169 | +2% |
| Plain question, no tools | $0.127 | $0.130 | +3% |

### Multi-agent work

Task: "use multiple agents" to count and summarize incident lines across 3 folders (30 files). Main session on Sonnet, one run each (2026-11-25), both answers fully correct:

| | Helpers used | Main + helper cost |
|---|---|---|
| Without overclock | 3 × Sonnet (Claude's default: same model as the main session) | $0.55 |
| With overclock | 3 × `overclock:scout` on Haiku | $0.20 (−64%) |

### Checkpoint + auto-resume

Test (2026-11-25, Sonnet): a two-turn coding session, then "continue where we left off" in a **new chat** vs. resuming the old one. Both finished the next step correctly.

| | First request processes |
|---|---|
| Resume the old conversation (what a cold re-read costs in full) | ~55k tokens |
| New chat + checkpoint | ~38k, of which ~14k new (the rest is Claude Code's shared system prompt) |

### Model tiers

Same 3-folder log job via `/overclock:orchestrate`, Sonnet main chat, one run each (2026-11-27). All answers correct.

| Run | Helpers chosen | Cost |
|---|---|---|
| `low`, advisor = Fable (your current setting) | 3 × Haiku; main chat did the reasoning | $1.40 (of which Fable advisor $1.03) |
| `high`, advisor = Fable | 3 × Sonnet + 1 × Opus for the hard reasoning | $2.39 (Fable advisor $1.64) |
| `low`, advisor off | 3 × Haiku + 1 × Opus for the hard reasoning | **$0.41** |

The routing follows the tier. The biggest saving is turning the advisor off on cheap tiers.

### Subscription usage meter check

[`bench/quota_ab.py`](bench/quota_ab.py) ran 24 Sonnet sessions (2026-11-25) alternating with/without overclock: 5-hour limit moved 4% vs 4%, weekly moved 0% vs 1% (within 1-point rounding noise), while API-equivalent cost dropped $1.39 -> $0.97 (−30%, 12/12 correct).

## Limits (honest list)

- **Failed commands aren't trimmed in Claude Code.** When a command exits with an error, Claude Code hands the hook text that's already cut, so built-in truncation applies instead.
- **No effect on context size or prices.** A plugin can't make the context window bigger; it can only keep it emptier.
- **Output trimming & transcript checkpointing are Claude-specific.** Antigravity uses overclock's Deepwork skills, multi-agent orchestration, and zero-overhead `SessionStart` project loader (`hooks.json`).
- **Cowork cloud limits.** Cowork loads skills, agents, and hooks, though output replacement is ignored for some tools in Cowork cloud sessions.
- **Hooks require `python3`**; if unavailable they fail open cleanly.

## Install

**Claude Code:**
```
/plugin marketplace add allanbest/overclock
/plugin install overclock@overclock
```

**Cowork / Claude app:**
Customize → Plugins → upload `dist/overclock.zip` (built via `./scripts/build-zip.sh`), or add marketplace `allanbest/overclock`.

**Antigravity:**
```bash
agy plugin install https://github.com/allanbest/overclock
```
Or copy/link the repo into `~/.gemini/config/plugins/overclock`.

*(Optional companion)*: install [Verisource](https://github.com/allanbest/verisource) (`fact-check` skill) for full credibility-tier verification and DOI citation formatting inside Deepwork research and literature grounding.

To skip Bash output trimming for one command in Claude Code, include `OVERCLOCK_RAW` (e.g. `OVERCLOCK_RAW=1 npm test`).

## Settings (environment variables)

| Variable | Effect |
|---|---|
| `OVERCLOCK_OFF=1` | Disable Bash output trimming, idle check, and transcript checkpointing |
| `OVERCLOCK_RULES=off` | Don't add Claude lean rules at `SessionStart` |
| `OVERCLOCK_DEEPWORK=off` | Don't auto-load `.overclock/active` project state at `SessionStart` / `PreCompact` |
| `OVERCLOCK_TRIM_ABOVE=6000` | Character count above which Bash output is trimmed |
| `OVERCLOCK_IDLE_MINUTES=60` | Idle time before the cold-cache warning |
| `OVERCLOCK_IDLE_MIN_TOKENS=60000` | Only warn for conversations bigger than this |
| `OVERCLOCK_IDLE_MODE=note` | Show the idle warning without holding the message |
| `OVERCLOCK_CHECKPOINT=off` | Don't write transcript checkpoints (also stops checkpoint auto-resume) |
| `OVERCLOCK_RESUME=off` | Keep writing checkpoints but don't load them in new chats |
| `OVERCLOCK_RESUME_DAYS=7` | Ignore transcript checkpoints older than this |
| `OVERCLOCK_TIER=<tier>` | Override the saved tier for one session |
| `OVERCLOCK_TIERS=off` | Don't load the tier routing block |
| `OVERCLOCK_FABLE=1` / `0` | Force the Fable tiers on or off |

## License

MIT
