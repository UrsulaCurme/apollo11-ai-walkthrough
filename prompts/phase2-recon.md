# Phase 2 — Repo Structure Reconnaissance

_Use this prompt AFTER pasting the Phase 1 context. This maps the codebase before diving into individual files._

---

## PROMPT

Clone https://github.com/chrislgarry/Apollo-11.

For both `Luminary099/` (Lunar Module) and `Comanche055/` (Command Module), do the following:

1. List every `.agc` file
2. Read the header comments of each file (the block at the top that starts with `# Copyright`, `# Filename`, `# Purpose`, etc.)
3. Extract: filename, stated purpose, approximate line count

Then group all files into these functional categories:

- **Executive/Scheduler**: job management, task scheduling, waitlist
- **Restart/Fault Handling**: restart logic, alarm handling, fresh start
- **Guidance/Navigation**: landing guidance, rendezvous, orbital mechanics, P-programs
- **Propulsion/Thrust Control**: engine ignition, throttle management, burns
- **Autopilot/Attitude Control**: digital autopilot (DAP), RCS jet control, attitude maneuvers
- **DSKY/Display**: keyboard input, display routines, verb/noun processing
- **IMU/Sensors**: IMU management, radar interface, optics, gyro calibration
- **Interpreter/Math**: the interpreter VM, math subroutines, trig, matrix ops
- **System Infrastructure**: interrupt handling, downlink/uplink, T4RUPT servicing, fresh start
- **Mission-Specific**: lunar landing, ascent, rendezvous, re-entry (things specific to LM or CM)

Output the result as a markdown file with two sections (Luminary099 and Comanche055), each containing a table grouped by category.

Note which files exist in BOTH modules (shared infrastructure) vs. which are unique to one module (mission-specific).

Flag any files whose purpose you cannot determine from the header comments alone.

Save the output as `walkthrough/00-repo-structure.md`.
