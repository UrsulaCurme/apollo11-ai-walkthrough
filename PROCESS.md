# PROCESS.md — How This Walkthrough Was Built

_A complete trace of using AI to analyze the Apollo 11 AGC source code, including every prompt, every tool decision, and every mistake._

---

## Project Goals

1. **Document** the Apollo 11 AGC source code in a way modern developers can understand
2. **Demonstrate** that no codebase is too old or too obscure for AI-assisted analysis
3. **Publish** the walkthrough as markdown files on GitHub
4. **Write** a blog post about the methodology for [The AI Realist](https://juliensimon.substack.com/)

## Tools Used

- **Claude Code** (Anthropic) — primary analysis tool, running against the cloned repo
- **Claude.ai** (Opus) — used for project planning, prompt design, and editorial review
- **GitHub** — hosting the walkthrough and the original source repo
- **Virtual AGC Assembly Language Manual** — primary architectural reference

## Timeline

| Date | Phase | Status |
|------|-------|--------|
| 2026-03-26 | Project setup, reference gathering, Phase 1 prompt | ✅ |
| 2026-03-26 | Phase 2: Repo structure reconnaissance | ✅ |
| 2026-03-26 | Phase 3: Deep dives — BURN_BABY_BURN, Executive, Restart | ✅ |
| 2026-03-27 | Phase 3: Deep dives — Landing Guidance, Interpreter, Waitlist, Executive (re-run), DSKY | ✅ |
| 2026-03-27 | Phase 4: Synthesis | ✅ |
| 2026-03-27 | Phase 5: Quality check | ✅ |
| 2026-03-27 | Phase 6: Blog post, review, publish | ✅ |

---

## Phase 0: Research & Planning (2026-03-26)

### What I Did

Started by asking whether anyone had already done an AI-assisted walkthrough of the Apollo 11 source code. Searched extensively — found no prior art. Plenty of human-authored explainers exist (Pluralsight course by Simon Allardice, Borja Sotomayor's Medium piece on FLAGORGY, the BrightCoding overview), but nobody had systematically fed the codebase through an LLM.

### Key References Identified

1. **Virtual AGC Assembly Language Manual** — `https://www.ibiblio.org/apollo/assembly_language_manual.html`
   - This is THE reference. Written by Ron Burkey, who built the Virtual AGC emulator. Covers the full Block II instruction set, memory map, interpreter language, and I/O channels
   - Derived from original MIT documents: E-2052 (Savage & Drake, 1967) and AGC4 Memo #9 (Blair-Smith, 1966)

2. **Wikipedia AGC article** — solid instruction-set summary table, good for cross-referencing

3. **Charles Averill's "Brief Analysis of the AGC"** — compact modern reference, cites both Blair-Smith memo and Burkey's manual

4. **Borja Sotomayor's Medium piece** — explains the interpreter's packed instruction format (7-bit opcodes, 15-bit addresses) and why the subroutine-library approach was rejected

### Why This Project Matters

The AGC code is public domain, arcane enough that most developers can't parse it, and the AI angle is genuinely novel. The code exercises AI code comprehension in a worst-case scenario: no syntax highlighting, no language server, a dead architecture, 1's-complement arithmetic, fixed-point math, and naming conventions from 1966. If Claude Code can navigate this, the "AI can only handle modern languages" objection evaporates.

---

## Phase 1: Context Prompt Design (2026-03-26)

### Problem

Claude Code (and all LLMs) have been trained overwhelmingly on modern code — x86, ARM, C, Python, JavaScript. AGC4 assembly is a dead language with almost no representation in training data. Without architectural context, the model will:
- Assume 2's-complement arithmetic (AGC uses 1's-complement)
- Misinterpret CCS as a simple conditional branch (it's a 4-way skip with DABS)
- Miss the TS skip-on-overflow pattern (the primary overflow handling idiom)
- Confuse native AGC instructions with interpreter pseudo-instructions
- Not understand bank switching

### Solution

Built a ~3,500-word context prompt that front-loads the critical architectural knowledge. Source: Virtual AGC Assembly Language Manual, cross-referenced with Wikipedia and the original MIT documents.

### Prompt Structure

The Phase 1 prompt (`prompts/phase1-context.md`) contains:

1. **Hardware overview** — word length, arithmetic model, clock speed, memory sizes
2. **Data representation** — SP/DP/TP formats, fractional scaling, the two-zeros problem
3. **Central registers** — A, L, Q, EB, FB, Z, BB, and the hardwired-zero at address 07
4. **Editing registers** — CYR, SR, CYL, EDOP with their auto-transform behaviors
5. **Counter/timer registers** — TIME1-6, CDU, PIPA with their interrupt triggers
6. **Memory map** — the 4 memory regions, bank switching, overlap areas
7. **Interrupt system** — all 11 vectors, masking, deferral conditions, save/restore protocol
8. **Basic instruction set** — every native opcode with octal encoding and behavioral notes
9. **Extracodes** — all EXTEND-prefixed instructions
10. **Derived instructions** — aliases like RETURN, NOOP, COM, RESUME, INHINT, RELINT
11. **The Interpreter** — how TC INTPRET switches modes, packed opcode format, key pseudo-instructions
12. **Source code formatting** — comment syntax, file inclusion, label conventions
13. **The two programs** — Comanche055 (CM) vs Luminary099 (LM), who did what
14. **Analytical rules** — 6 concrete instructions for how to approach each file

### Design Decisions

- **Included octal encodings**: Without them, Claude Code can't verify raw numeric operands in the source
- **Called out TS skip and CCS 4-way explicitly**: These are the AGC's if/else and switch — control flow analysis collapses without them
- **Left out pseudo-ops table**: ERASE, EQUALS, 2DEC, SETLOC, BANK etc. matter for assembler work but add noise for a walkthrough. Can be looked up on demand
- **Left out full I/O channel map**: Same reasoning. Channel 5-7 for bank switching are covered; the rest can be fetched as needed
- **Ended with methodology, not just reference**: The 6 analytical rules give Claude Code a *process*, not just data

### What to Watch For

Known risk areas where the model may still struggle despite the context:
- Bank-switching logic (FB/EB/BB/superbank interactions)
- The interpreter's packed opcode decoding via EDOP register
- Fixed-point scaling conventions (the implicit binary point tracking)
- Interrupt timing and the "unprogrammed sequences" (PINC, MINC, etc.)
- The DSKY Verb/Noun display system

---

## Phase 2: Repo Structure Reconnaissance

### Prompt Used

```
Clone https://github.com/chrislgarry/Apollo-11. Map the repo structure. For both 
Luminary099/ and Comanche055/, list every .agc file with its stated purpose from 
the header comments. Group them into functional categories: navigation, guidance, 
propulsion control, DSKY interface, executive/scheduler, restart/fault handling, 
math/utility. Output a markdown table.
```

### Results

_To be filled after execution._

### Observations

_To be filled after execution._

---

## Phase 3: Deep Dives

### Module Selection Rationale

Chose 5 key files based on narrative impact + technical depth:

1. **FRESH_START_AND_RESTART.agc** — the code that saved Apollo 11 (1202 alarm). Maximum dramatic value
2. **LUNAR_LANDING_GUIDANCE_EQUATIONS.agc** — P63/P64/P66, the actual landing math. Technical centerpiece
3. **BURN_BABY_BURN--MASTER_IGNITION_ROUTINE.agc** — engine ignition + cultural Easter eggs. Human interest
4. **EXECUTIVE.agc + WAITLIST.agc** — the job scheduler. Shows the "hidden OS". Architecture story
5. **INTERPRETER.agc** — the VM inside the machine. Computer science story

### Prompts Used

See `prompts/phase3-deep-dives.md` for the full prompts. Each was injected into Claude Code via `claude -p` with the Phase 1 context + cached AGC manual as system context.

### Run Log

All runs used **claude-opus-4-6** (Opus 4.6 with extended thinking) via Claude Code CLI.

| Dive | Source Files | Prompt Size | Output | Time | Notes |
|------|-------------|-------------|--------|------|-------|
| 3d BURN_BABY_BURN | 22K chars | 97K chars | 29K chars | 222s | First run failed (329 chars) — Claude tried to write a file instead of responding. Fixed prompt to say "Respond with the markdown directly" |
| 3a Executive | 12K chars | 87K chars | 30K chars | 225s | Re-run after splitting from combined Executive+Waitlist |
| 3a2 Waitlist | 15K chars | 90K chars | 33K chars | 243s | Clean run |
| 3b Restart/1202 | 33K chars | 108K chars | 33K chars | 232s | Clean run |
| 3c Landing Guidance | 32K chars | 108K chars | 57K chars | 401s | Longest output — 1,419 lines |
| 3e Interpreter | 75K chars | 160K chars | 39K chars | 273s | Largest input (INTERPRETER.agc is 3,075 lines) |
| 3f DSKY/Pinball | 130K chars | 207K chars | 40K chars | 346s | Two source files totaling ~4,700 lines |
| Synthesis | All walkthroughs | 264K chars | 38K chars | 792s | Fed all 7 walkthrough files as input |
| **Total** | | | **~299K chars** | **~47 min** | |

### What the AI Got Right

- **Instruction semantics.** CCS 4-way skip, TS overflow-skip, INDEX modification — all correctly identified and explained across every file
- **Control flow tracing.** The vtable pattern in BURN_BABY_BURN, the EJSCAN priority scan in EXECUTIVE, the T3RUPT dispatch chain in WAITLIST — all traced accurately through actual instruction sequences
- **Cultural references.** Every Latin inscription, literary allusion, and programmer joke was identified and contextualized (HONI SOIT QUI MAL Y PENSE, NOLI SE TANGERE, EXTIRPATE, ASSASSINATE CLOKTASK, GOTOPOOH)
- **Interpreter architecture.** The EDOP register as hardware opcode unpacker, the packed 7+7+1 bit format, the three-stage dispatch cascade — all correctly explained
- **Modern parallels.** FreeRTOS comparison tables, crash-only design (Candea/Fox 2003), Erlang "let it crash," virtual DOM analogy for DSPTAB — all substantive, not superficial
- **Honest uncertainty.** The interpreter walkthrough explicitly flagged uncertain interpretations (store code encoding, POLY coefficient verification, pushdown overflow protection)

### What the AI Got Wrong

1. **First BURN_BABY_BURN run produced 329 chars.** Claude Code tried to use file-write tools instead of responding to stdout. The response was literally "The file write keeps getting blocked by permissions." Root cause: the prompt said "Do NOT use any tools" which confused the model into thinking it couldn't output text either. Fix: changed prompt to "Respond with the full markdown document directly in your text response."

2. **Core set count ambiguity (7 vs 8).** The Executive walkthrough initially said `DEC 7` means "8 total core sets" (interpreting it as a CCS loop counter). The Waitlist and Synthesis said "7 core sets." Both interpretations are defensible — there are 7 schedulable slots plus the running job's registers. Standardized to "7 core sets for pending/sleeping jobs" for consistency.

3. **I/O channel 14 description.** BURN_BABY_BURN walkthrough described channel 14 as "controls the DPS throttle" — oversimplified. Channel 14 is a multi-function output channel handling IMU CDU drive, gyro activity, AND engine commands. Bit 4 specifically is the engine-on command. Corrected to be more precise.

4. **"World's first Verb-Noun CLI."** DSKY walkthrough made this strong claim. Defensible given the date (DSKY flew 1966, predating Unix shells) but unprovable as "first." Softened to "one of the earliest."

5. **Timeout on first attempt.** The original 900-second timeout was too short for Opus 4.6 with extended thinking on complex analysis. First BURN_BABY_BURN run hit the timeout at 890s. Increased to 1800s.

### Corrections Applied

All corrections documented in `QUALITY_CHECK.md`. Summary:
- Fixed title line count in 01-executive.md (600 → ~500)
- Softened "world's first" claim in 07-dsky-interface.md
- Clarified I/O channel 14 description in 05-burn-baby-burn.md
- Standardized core set count language across files

---

## Phase 4: Synthesis

### Prompt Used

Fed all 7 completed walkthrough files as input, plus the Phase 1 context. Prompted for a three-theme synthesis: (1) what the AGC got right that we've forgotten, (2) what the constraints forced, (3) what would surprise a modern developer. Output: `walkthrough/08-lessons.md`, 273 lines, 38K chars, 792 seconds.

### Key Themes Identified

- Cooperative multitasking as green threads (Go goroutines, Python asyncio)
- Checkpoint/restart as crash-only design (predating Candea/Fox 2003 and Erlang by decades)
- The interpreter as one of the earliest bytecode VMs
- Verb-Noun as proto-CLI (DSPTAB dirty flags as proto-virtual-DOM)
- Fixed-pool allocation vs dynamic allocation — "the worst case is knowable"

---

## Phase 5: Blog Post

### Angle

"I used AI to walk through the code that landed humans on the Moon. Here's what happened."

The post should demonstrate:
- The prompt engineering required to make this work (Phase 1 context)
- What the AI nailed (pattern recognition in unfamiliar assembly, cross-referencing modules)
- What the AI got wrong (specific examples with corrections)
- What the AGC code reveals about software engineering that we've forgotten
- Why this matters for the "AI replacing developers" discourse — AI as *reading* tool, not writing tool

### Target

Substack (The AI Realist) + LinkedIn promotion. Potential YouTube companion.

### Draft

See `blog/blog-post.md`.

---

## Phase 6: Review & Publish

### Fact-Checking Approach

Cross-referenced AI output against:
- Virtual AGC Assembly Language Manual (ibiblio.org)
- Wikipedia AGC article (instruction set table, hardware specs)
- Run log data (scripts/run_log.jsonl)
- Internal consistency across all 8 walkthrough files

Full results in `QUALITY_CHECK.md`.

### Corrections Log

See "Corrections Applied" in Phase 3 above. Five issues found and fixed:
1. Tool-use confusion on first BURN_BABY_BURN run (prompt fix)
2. Core set count ambiguity 7 vs 8 (standardized)
3. I/O channel 14 oversimplification (clarified)
4. "World's first" CLI claim (softened)
5. Timeout too short for Opus 4.6 (increased)

---

## Lessons Learned

1. **Context-priming is everything for dead languages.** Without the 3,500-word Phase 1 prompt, the model defaults to modern assembly conventions and hallucinates. With it, instruction semantics are correct across thousands of lines of analysis.

2. **The raw reference manual matters.** The Phase 1 prompt was my condensed summary; injecting actual sections of the ibiblio manual as ground truth caught edge cases the summary missed (EDOP shift behavior, CCS branch ordering).

3. **Opus 4.6 with extended thinking is necessary for this depth.** Sonnet was fine for the repo recon (categorization task). But the deep dives — tracing control flow through 1960s assembly, identifying cultural references, making modern parallels — required Opus. The quality difference is stark.

4. **Claude Code `-p` mode needs careful prompt engineering.** The model tried to use file-write tools instead of responding to stdout. The fix was explicit: "Respond with the full markdown document directly in your text response." This is a Claude Code-specific gotcha.

5. **Total cost: ~47 minutes of Opus compute on a Max plan.** No API billing. The entire project — 8 walkthrough files totaling ~6,000 lines / ~300K chars of technical analysis — was produced in under an hour of compute time across two days.

6. **Where LLMs genuinely help with legacy code: reading, not writing.** The AI didn't write any AGC assembly. It *read* it — and translated it into something modern developers can understand. This is the underappreciated use case: AI as a reading tool for code that predates its training data.


---

## Automation Setup (2026-03-26)

### Scripts

Two Python scripts automate the API-based approach:

**`scripts/run_phase2_recon.py`** — Phase 2 repo reconnaissance
- Scans all .agc files in both Luminary099/ and Comanche055/
- Extracts header comments (first ~40 lines of each file)
- Sends the full inventory to Claude for categorization
- Uses Sonnet by default (sufficient for categorization, cheaper)

**`scripts/run_deep_dives.py`** — Phase 3 deep dives
- Fetches and caches the Virtual AGC Assembly Language Manual from ibiblio.org
- Extracts key sections (instruction set, memory map, interrupts, interpreter)
- For each dive: assembles system prompt (Phase 1 context + raw manual sections) + user message (source files + dive-specific prompt)
- Calls Claude API with extended thinking enabled (10K thinking budget)
- Saves walkthrough output, thinking trace, and structured run log (JSONL)
- Uses Opus by default (necessary for accurate AGC assembly analysis)

### Why Two Layers of Reference

The system prompt contains TWO forms of AGC architecture reference:

1. **Phase 1 context** (`prompts/phase1-context.md`) — my condensed summary. Gives the model a framework: register names, instruction behaviors, key idioms to watch for. ~3,500 words
2. **Raw manual sections** (cached from ibiblio.org) — the actual Virtual AGC Assembly Language Manual text. Ground truth. The prompt explicitly says: "If the condensed reference conflicts with this material, trust this material."

The condensed summary helps the model reason efficiently. The raw manual prevents hallucination on specifics like CCS branch ordering, TS overflow behavior, or EDOP shift semantics.

### Convenience Wrapper

`./run.sh` provides a simple CLI:
```
./run.sh setup      # clone repo, install deps, cache manual
./run.sh recon      # Phase 2: scan repo structure
./run.sh dive 3a    # single deep dive
./run.sh dive all   # all 5 deep dives
./run.sh status     # show what's been generated
```

### Token Budget Estimates

| Dive | Source Files | Est. Input Tokens | Notes |
|------|-------------|-------------------|-------|
| 3a | EXECUTIVE + WAITLIST | ~25K | Two medium files |
| 3b | FRESH_START_AND_RESTART + ALARM_AND_ABORT | ~30K | Large restart file |
| 3c | LUNAR_LANDING_GUIDANCE_EQUATIONS | ~20K | Dense interpreter code |
| 3d | BURN_BABY_BURN | ~15K | Shortest dive |
| 3e | INTERPRETER + INTER-BANK_COMMUNICATION | ~35K | Largest single file |

System prompt (Phase 1 + manual) adds ~15-20K tokens to each call.
Output budget: 16K tokens per dive. Thinking budget: 10K tokens.
