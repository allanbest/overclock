---
name: handoff
description: Write a compact handoff note so work can continue in a fresh, cheaper session. Use when the user says "handoff", "wrap up for a new chat", "save progress", "this chat is getting long", or when a long task reaches a natural break. Long conversations get more expensive every turn because the whole history is re-sent, so moving to a new session with a short note saves a lot.
---

# Handoff

Every message in a long conversation re-sends the whole history. A fresh session that starts from a 300-word note costs a small fraction of that. This skill writes that note.

## Active Deepwork projects

If `.overclock/active` exists in the workspace, **also** update `.overclock/projects/<slug>/state.md` (and verify it with `python3 ../deepwork/scripts/project.py check-state`, or run `/overclock:reflect`) so a fresh session on either Claude Code or Antigravity auto-loads the project state automatically.

## Steps

1. Write `HANDOFF.md` in the project or working folder (overwrite an older one; if there's no sensible folder, put the note in the chat instead). Keep it under about 300 words, using exactly these sections:

```markdown
# Handoff: <short task name>
_Updated: <date>_

## Goal
<what the user wants, plus any constraints or preferences they stated>

## Done
- <finished items, with file paths>

## Current state
<where things stand right now; anything half-finished>

## Decisions
- <choice made> because <reason>

## Next steps
1. <the very next action>
2. ...

## Key files and commands
- `path/to/file`: <why it matters>
- `command`: <what it does>

## Open problems
- <errors or failing tests, verbatim, still unresolved>
```

2. Include only what a newcomer needs to continue. Leave out exploration dead ends, tool output that's already been used, and anything easy to rediscover.
3. Tell the user, in one or two lines, to start a new session and say: **"Continue from HANDOFF.md"** (or simply start a new chat if a Deepwork project or overclock checkpoint is active).

## When continuing from a handoff

If the user says "continue from HANDOFF.md" (or similar), read that file first, confirm the next step in one line, and carry on. Don't re-explore what the note already covers unless something looks wrong.
