---
name: tier
description: Show or set overclock's model tier (low, medium, high, extra, max), which decides which Claude model each helper uses. Use only when the user runs /overclock:tier or asks to change the overclock tier/level.
argument-hint: "[low|medium|high|extra|max|off | fable on|off]"
disable-model-invocation: true
---

# overclock model tier

The user's argument: `$ARGUMENTS`

1. Run the tier script from the plugin (it lives two folders up from this skill, in `hooks/`):
   - no argument: `python3 "<this skill's folder>/../../hooks/tiers.py" show`
   - with a tier or `off`: `python3 "<this skill's folder>/../../hooks/tiers.py" set <tier>`
   - `fable on` / `fable off`: `python3 "<this skill's folder>/../../hooks/tiers.py" fable on` (Fable often bills usage credits, so it's off until the user turns it on)
2. Show the user the result in a short table: tier, what it prioritises, main-chat model, helper models. Only list `extra` and `max` if the script lists them (they need Fable).
3. If the recommended main-chat model differs from the model this chat is running on, say so in one line and tell the user to switch with `/model <name>` **at the start of a new chat**, because switching mid-chat re-reads the whole conversation at full price.
4. From now on in this chat, follow the routing lines the script printed: pass `model` explicitly on every `overclock:scout` / `overclock:worker` call. New chats load the tier automatically.
