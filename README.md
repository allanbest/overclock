<p align="center"><img src="assets/icon.png" width="96" alt=""></p>

# overclock

**Make Claude cheaper per task without making it worse.** overclock is a small Claude plugin for Cowork and Claude Code. It keeps junk out of Claude's context, so every later message in the conversation costs less.

## Why this works

Each message you send re-sends the whole conversation to the model. When a command prints a 2,000-line log, you pay for that log again on every following turn. Most "make Claude cheaper" tricks try to make Claude *write* less. In agent work, though, most of the cost is what Claude *reads*. overclock goes after that.

## What's inside

| Part | What it does |
|---|---|
| **Output trimmer** (hook) | When a command prints a lot (over ~6,000 characters), Claude gets a compact version: the start, the end, **every error/warning line** with context, and repeated lines collapsed (`[×3000]`). The full output stays in a file, and Claude gets its path. Short outputs are never touched. |
| **Lean rules** (hook, ~150 tokens, once per session) | Lead with the answer, batch tool calls, read only what's needed, and trust the trimmed output. |
| **scout** (subagent) | A cheap Haiku explorer for searches that need many file reads. It returns a short summary instead of filling the main conversation. |
| **Idle-session warning** (hook) | Claude's cache of your conversation lasts about an hour. If you come back to a **big** conversation (60k+ tokens) after that, your next message re-processes the whole thing at full cost. overclock holds that message once, before any usage is spent, and suggests a new chat or a handoff. Send it again to continue anyway. |
| **/overclock:orchestrate** (skill) + **worker** (Sonnet subagent) | Cheap multi-agent work. It first decides whether splitting is worth it at all (multi-agent setups use about 15× the tokens of a chat, per Anthropic). If it is, it gives each helper its own piece, caps it at 3–5 helpers, uses the cheapest suitable model (Haiku scout or Sonnet worker), and has helpers write details to files and return under 150 words. One final check at the end, no agent teams. |
| **/overclock:handoff** (skill) | Writes a ~300-word `HANDOFF.md` so a long task can continue in a fresh, cheap session. Say "Continue from HANDOFF.md" in the new chat. |
| **Compaction guide** (hook) | When the conversation gets compacted, tells the summary what to keep (goal, decisions, paths, open errors) and what to drop. |

## Measured results

Real Claude Code sessions (Opus 5.5) with and without overclock, interleaved, 3–6 runs each, on 2026-11-24. Every answer was correct in both versions.

| Task | Without | With overclock | Change |
|---|---|---|---|
| Run a script with a 95 KB log, find the 3 warnings | $0.268 | $0.184 | **−31%** |
| Same with a 16 KB log | $0.230 | $0.187 | **−19%** |
| Find a value in a 30-file codebase | $0.166 | $0.169 | +2% |
| Plain question, no tools | $0.127 | $0.130 | +3% |

**In short:** sessions that run commands with long output get much cheaper. Simple chats cost about 2–3% more, which is the price of the rules.

### Multi-agent work

Task: "use multiple agents" to count and summarize incident lines across 3 folders (30 files). Main session on Sonnet, one run each (2026-11-25), both answers fully correct:

| | Helpers used | Main + helper cost |
|---|---|---|
| Without overclock | 3 × Sonnet (Claude's default: same model as the main session) | $0.55 |
| With overclock | 3 × `overclock:scout` on Haiku | $0.20 (−64%) |

That's a single run per version, so treat it as an early sign, not a benchmark. When `/overclock:orchestrate` was asked to write per-folder reports, it correctly decided one search was enough and used no helpers at all. Not splitting a small job is the cheapest outcome. With Opus as the main model, the gap should be larger, since Claude's default helpers then run on Opus too.

### Does it stretch subscription usage limits?

Probably, but the meter is too coarse to prove it at small scale. [`bench/quota_ab.py`](bench/quota_ab.py) runs the same tasks with and without overclock in alternating blocks and reads Claude's own usage meter (5-hour and weekly) after each block. A first run with 24 Sonnet sessions (2026-11-25):

| | Without | With overclock |
|---|---|---|
| 5-hour limit used | 4% | 4% |
| Weekly limit used | 0% | 1% |
| Same runs priced at API rates | $1.39 | $0.97 (−30%) |
| Cache writes / output tokens | 301k / 9.7k | 210k / 6.7k (−30% / −31%) |
| Correct answers | 12/12 | 12/12 |

The meter only reports whole percentage points, and each block moved it by just 1–3 points, so the quota numbers are a tie within rounding noise. The token mix explains why overclock should still help your limits. Anthropic doesn't say whether cache reads (re-reading the conversation so far) count toward limits, but overclock's savings come mainly from **cache writes and output tokens**, which almost certainly do. A conclusive meter result would need roughly 10× more runs.

What I tried that didn't work:
- Changing *small* outputs, even just removing colour codes, confused Claude into re-checking, and cost 30% more. overclock now leaves them alone.
- A "use quiet flags / tail" rule made Claude cut off the line it needed. It was removed.
- Without the rules, Claude distrusts trimmed output and reads the full log anyway. The rules are what make the trimming pay off.

## Limits (honest list)

- **Failed commands aren't trimmed.** When a command exits with an error (for example failing tests), Claude Code hands the hook text that's already cut, so overclock can't improve it. Claude Code's built-in truncation applies instead.
- **No effect on context size or prices.** A plugin can't make the context window bigger; it can only keep it emptier.
- **Cowork hasn't been tested directly.** Cowork loads plugin hooks, skills and agents, and these tests ran in Claude Code. The hooks need `python3`; if it's missing they do nothing (fail-safe). In Cowork cloud sessions, output replacement is ignored for some tools.
- **scout** only helps on large searches and wasn't triggered in the small test codebase.
- The **handoff** and **compaction** parts are simple and haven't been benchmarked.
- The **idle warning** was tested in Claude Code. The held message used no usage (0 turns), and the second send went through. Its savings depend on how often you return to big, stale conversations, so they aren't benchmarked. How Cowork displays the warning is untested.

## Install

**Cowork / Claude app:** Customize → Plugins → upload `overclock.zip` (from the releases page), or add the marketplace `allanbest/overclock`.

**Claude Code:**
```
/plugin marketplace add allanbest/overclock
/plugin install overclock@overclock
```

To turn it off, disable the plugin in the Plugins panel or run `/plugin`. To skip trimming for one command, include `OVERCLOCK_RAW` in it (for example `OVERCLOCK_RAW=1 npm test`).

## Settings (Claude Code only, via environment variables)

| Variable | Effect |
|---|---|
| `OVERCLOCK_OFF=1` | Disable output trimming |
| `OVERCLOCK_RULES=off` | Don't add the lean rules |
| `OVERCLOCK_TRIM_ABOVE=6000` | Character count above which output is trimmed |
| `OVERCLOCK_IDLE_MINUTES=60` | Idle time before the warning |
| `OVERCLOCK_IDLE_MIN_TOKENS=60000` | Only warn for conversations bigger than this |
| `OVERCLOCK_IDLE_MODE=note` | Show the warning without holding the message |

## License

MIT
