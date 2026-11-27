---
name: stop
description: Pause, complete, or archive the active Deepwork project and clear .overclock/active so session hooks return to zero-token silence. Use when the user invokes /overclock:stop or asks to pause, finish, or close out an active deepwork project.
---

# Stop Deepwork Project

Cleanly closes out or pauses the active `.overclock/projects/<slug>/` project while preserving all notebook files (`brief.md`, `lab.md`, `spec.md`, `tasks.md`, `decisions.md`, `report.md`) on disk.

## Steps

1. Check active state:
   `python3 ../deepwork/scripts/project.py status`
2. If completing (`--complete`), ensure final results/verification evidence are recorded in `lab.md` / `tasks.md` / `report.md` and `state.md`.
3. Update `state.md` with the final `Completed`, `Dead Ends / Avoid`, and `Next Step` (if pausing).
4. Run the stop command (default `--pause` if the user plans to resume later; `--complete` if finished; `--archive` if shelving):
   `python3 ../deepwork/scripts/project.py stop --pause`
   *(or `--complete` / `--archive`)*
5. Confirm to the user that `.overclock/active` was cleared so future sessions start with zero Deepwork hook overhead, and mention `python3 <plugin>/skills/deepwork/scripts/project.py resume <slug>` if they want to reactivate it later.
