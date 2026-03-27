# Apollo 11 AGC Source Code — AI Walkthrough

An AI-assisted deep dive into the original Apollo 11 Guidance Computer source code, produced using [Claude Code](https://docs.anthropic.com/en/docs/claude-code) by Anthropic.

## What This Is

The Apollo 11 AGC source code — ~40,000 lines of 1960s assembly language for a 15-bit, 1's-complement computer with 72 KB of memory — is one of the most important codebases in history. It's also nearly unreadable to modern developers.

This project uses AI to bridge that gap: a structured, module-by-module walkthrough that explains what the code does, how it does it, and why the engineering decisions still matter.

**No code is too old for AI analysis.**

## Walkthrough Modules

### [00 — Repo Structure](walkthrough/00-repo-structure.md)
A map of all 175 `.agc` files in the Luminary099 codebase, grouped by function: navigation, guidance, autopilot, systems management, and the operating system layer.

### [01 — The Executive](walkthrough/01-executive.md)
The AGC had no operating system — the Executive *was* the operating system. It implements cooperative multitasking across 7 fixed core sets, using priority-based scheduling in ~600 lines of assembly. The design anticipates Go's goroutine scheduler and Python's asyncio by decades. We learned that with fixed resource pools and static analysis, you can prove your scheduler will never run out of slots — something no modern system with 10,000 goroutines can claim.

### [02 — The Waitlist](walkthrough/02-waitlist.md)
The timer-driven task scheduler that ran the AGC's real-time heartbeat. The Waitlist fires tasks at precise intervals using the hardware TIME3 counter, managing up to 9 concurrent timed events with a hand-computed worst-case execution time analysis written in the source comments — in 1966, before real-time systems theory existed as a discipline.

### [03 — Fresh Start & Restart](walkthrough/03-restart.md)
The module that saved Apollo 11. When the 1202 alarms fired during descent, this code restarted the computer, verified the integrity of a checksummed phase table, reinitialised all scheduling, and resumed the guidance equations within milliseconds — while the descent engine kept firing. This is crash-only design and "let it crash" philosophy, implemented 20 years before Erlang and 37 years before the pattern was formally described.

### [04 — Landing Guidance Equations](walkthrough/04-landing-guidance.md)
The math that flew the Lunar Module to the surface. Programs P63 (braking), P64 (approach with redesignation), and P66 (manual rate-of-descent) implement a gravity-turn guidance algorithm running at 2 Hz in interpreted bytecode. We learned how the code handles the transition from automatic to manual control — the moment Armstrong took the stick to dodge a boulder field.

### [05 — BURN_BABY_BURN](walkthrough/05-burn-baby-burn.md)
The master ignition routine that starts every engine burn in the mission. It uses table-driven virtual method dispatch — structurally identical to a C++ vtable — so one generic routine handles descent, ascent, and orbital burns. Also the most culturally rich file in the codebase: Latin inscriptions, a reference to the Order of the Garter, and the word "EXTIRPATE" where a modern programmer would write "clear."

### [06 — The Interpreter](walkthrough/06-interpreter.md)
The flight software wouldn't fit in 36K words of ROM as native assembly, so MIT built a bytecode virtual machine inside the AGC. It packs two 7-bit opcodes per 15-bit word, provides vector/matrix math and trig functions, and runs 10–25x slower than native code — but saved an estimated 15,000–40,000 words of ROM. Without it, there is no Moon landing. This predates the Java JVM by nearly 30 years.

### [07 — Pinball Game (DSKY Interface)](walkthrough/07-dsky-interface.md)
The astronaut's only interface to the AGC: 19 keys and a set of 7-segment displays. The Verb-Noun command language is one of the earliest structured human-computer interfaces. The display buffer (`DSPTAB`) uses sign bits as dirty flags to diff changes — the same principle as React's virtual DOM, in 14 words of 1966 assembly. At ~3,800 lines, it's one of the largest modules in Luminary.

### [08 — Lessons for 2026](walkthrough/08-lessons.md)
A synthesis essay drawing on all seven walkthroughs. Covers architectural patterns ahead of their time (cooperative multitasking, checkpoint/restart, bytecode VMs, command languages), constraints as a design force, the 1202 story as a case study in graceful degradation, the human element in the comments, and what a 2026 engineer building safety-critical systems can still learn from code written for a 15-bit computer with 2K of RAM.

## How This Was Made

See [PROCESS.md](PROCESS.md) for a detailed trace of the methodology: the prompts used, the tools involved, what worked, what didn't, and what the AI got wrong.

See also the [blog post](blog/blog-post.md) for the narrative version.

## References

- [Apollo 11 AGC Source Code](https://github.com/chrislgarry/Apollo-11) — Chris Garry's GitHub repo (public domain)
- [Virtual AGC Assembly Language Manual](https://www.ibiblio.org/apollo/assembly_language_manual.html) — Ron Burkey's comprehensive reference
- [AGC4 Basic Training Manual (E-2052)](https://www.ibiblio.org/apollo/NARA-SW/E-2052.pdf) — Original 1967 MIT training document
- [Virtual AGC Project](https://www.ibiblio.org/apollo/) — Emulators, scans, documentation
- [AGC4 Memo #9](https://www.ibiblio.org/apollo/Documents/agc4_memo9_rev_june1967.pdf) — Block II Instructions, by Hugh Blair-Smith

## Author

[Julien Simon](https://www.linkedin.com/in/juliensimon/) — AI Operating Partner at [Fortino Capital](https://www.fortinocapital.com/). Writing at [The AI Realist](https://juliensimon.substack.com/).

## License

The Apollo 11 source code is public domain (US government work). This walkthrough and all original analysis text are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
