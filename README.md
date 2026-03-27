# Apollo 11 AGC Source Code — AI Walkthrough

An AI-assisted deep dive into the original Apollo 11 Guidance Computer source code, produced using [Claude Code](https://docs.anthropic.com/en/docs/claude-code) by Anthropic.

## What This Is

The Apollo 11 AGC source code — ~40,000 lines of 1960s assembly language for a 15-bit, 1's-complement computer with 72 KB of memory — is one of the most important codebases in history. It's also nearly unreadable to modern developers.

This project uses AI to bridge that gap: a structured, module-by-module walkthrough that explains what the code does, how it does it, and why the engineering decisions still matter.

**No code is too old for AI analysis.**

## Walkthrough Modules

| # | File | Module | What It Covers |
|---|------|--------|----------------|
| 1 | [00-repo-structure.md](walkthrough/00-repo-structure.md) | Repo Map | Complete file inventory and functional groupings |
| 2 | [01-executive.md](walkthrough/01-executive.md) | The Executive | Priority-based job scheduler — the hidden OS |
| 3 | [02-waitlist.md](walkthrough/02-waitlist.md) | The Waitlist | Timer-driven preemptive task scheduler |
| 4 | [03-restart.md](walkthrough/03-restart.md) | Fresh Start & Restart | The alarm handler that saved the Apollo 11 landing |
| 5 | [04-landing-guidance.md](walkthrough/04-landing-guidance.md) | Landing Guidance Equations | P63/P64/P66 — the math that flew the LM to the surface |
| 6 | [05-burn-baby-burn.md](walkthrough/05-burn-baby-burn.md) | Master Ignition Routine | Engine ignition sequencing + the cultural Easter eggs |
| 7 | [06-interpreter.md](walkthrough/06-interpreter.md) | The Interpreter | The virtual machine within the machine |
| 8 | [07-dsky-interface.md](walkthrough/07-dsky-interface.md) | Pinball Game | DSKY keyboard and display system |
| 9 | [08-lessons.md](walkthrough/08-lessons.md) | Lessons for 2026 | What modern engineers can learn from 1969 code |

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
